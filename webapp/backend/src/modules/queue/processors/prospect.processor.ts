import { Processor, Process } from '@nestjs/bull';
import { Job } from 'bull';
import { Logger } from '@nestjs/common';
import { BusinessContextService } from '../../business-context/business-context.service';
import { LeadsService } from '../../leads/leads.service'; // Assuming LeadsService exists
import { McpService } from '../../mcp/mcp.service';
import { HarvesterJobData } from '../../prospect/prospect.service'; // Import from ProspectService
import { BusinessContext as BusinessContextType, CreateLeadDto, LeadData } from '../../../shared/types/nellia.types'; // Assuming these types exist

// Placeholder types based on the plan, these might need to be defined more concretely
// or imported if they exist elsewhere (e.g., from an MCP client library or shared types)
interface HarvesterParams {
  query: string;
  maxSites: number;
  context: BusinessContextType; // Context might be more specific if MCP expects a certain shape
  // outputFormat?: string; // As seen in direct python call
}

interface HarvesterResult {
  url: string;
  content_summary?: string; // Example field, actual fields depend on harvester.py output
  title?: string;
  // Add other fields that harvester.py returns for each site
  [key: string]: any; // Allow other properties
}


@Processor('prospect-processing')
export class ProspectProcessor {
  private readonly logger = new Logger(ProspectProcessor.name);

  constructor(
    private businessContextService: BusinessContextService,
    private leadsService: LeadsService,
    private mcpService: McpService,
  ) {}

  @Process('run-harvester')
  async handleHarvesterProcess(job: Job<HarvesterJobData>): Promise<any> {
    this.logger.log(`Starting harvester process for job ${job.id} with data: ${JSON.stringify(job.data)}`);
    
    try {
      await job.progress(10);
      this.logger.debug(`Job ${job.id} progress: 10%`);

      const context = await this.businessContextService.getContextForMcp();
      if (!context) {
        this.logger.error(`Business context not found for job ${job.id}. Context ID from job: ${job.data.contextId}`);
        // The plan implies contextId in job.data might be 'default' or null.
        // getContextForMcp fetches the single global context.
        // If job.data.contextId was meant to fetch a *specific* context, BusinessContextService would need a findById method.
        // For now, proceeding with the assumption that getContextForMcp is sufficient.
        throw new Error('Business context not found or not configured.');
      }
      this.logger.debug(`Job ${job.id}: Business context fetched.`);
      await job.progress(20);

      const enhancedQuery = this.buildSearchQuery(job.data.searchQuery, context);
      this.logger.debug(`Job ${job.id}: Enhanced search query: "${enhancedQuery}"`);
      await job.progress(30);

      this.logger.log(`Job ${job.id}: Executing harvester for query "${enhancedQuery}" (max sites: ${job.data.maxSites})`);
      const harvesterResults = await this.executeHarvester({
        query: enhancedQuery,
        maxSites: job.data.maxSites,
        context: context,
      });
      this.logger.log(`Job ${job.id}: Harvester executed, found ${harvesterResults.length} results.`);
      await job.progress(60);

      this.logger.log(`Job ${job.id}: Processing ${harvesterResults.length} harvester results through MCP agents.`);
      const processedLeadsDto = await this.processHarvesterResults(harvesterResults, context);
      this.logger.log(`Job ${job.id}: ${processedLeadsDto.length} leads processed by MCP agents.`);
      await job.progress(80);

      this.logger.log(`Job ${job.id}: Saving ${processedLeadsDto.length} processed leads to database.`);
      const savedLeads = await this.saveLeadsToDatabase(processedLeadsDto);
      this.logger.log(`Job ${job.id}: ${savedLeads.length} leads saved to database.`);
      await job.progress(100);

      const completionMessage = `Harvester process completed for job ${job.id}. Saved ${savedLeads.length} leads.`;
      this.logger.log(completionMessage);

      return {
        success: true,
        leadsCreated: savedLeads.length,
        jobId: job.id,
        message: completionMessage,
        completedAt: new Date().toISOString(),
      };

    } catch (error) {
      this.logger.error(`Harvester process failed for job ${job.id}: ${error.message}`, error.stack);
      await job.moveToFailed({ message: error.message }, true); // Move to failed and allow retry if attempts left
      throw error; // Re-throw to ensure NestJS Bull marks it as failed
    }
  }

  private buildSearchQuery(baseQuery: string, context: BusinessContextType): string {
    // Enhance search query with business context
    const industryTerms = context.industry_focus?.join(' OR ') || '';
    const targetMarket = context.target_market || '';
    
    let query = baseQuery;
    if (industryTerms) query += ` (${industryTerms})`;
    if (targetMarket) query += ` ${targetMarket}`;
    
    return query.trim();
  }

  private async executeHarvester(params: HarvesterParams): Promise<HarvesterResult[]> {
    this.logger.debug(`Executing harvester with params: ${JSON.stringify({query: params.query, maxSites: params.maxSites})}`);
    // Option 1: Call via MCP
    try {
      this.logger.log('Attempting harvester execution via MCP.');
      // Ensure mcpService.runHarvester is correctly typed and implemented
      const mcpResults = await this.mcpService.runHarvester(params.query, params.maxSites, params.context);
      this.logger.log(`MCP harvester successful, ${mcpResults?.length || 0} results.`);
      return mcpResults || []; // Ensure it returns an array
    } catch (mcpError) {
      this.logger.warn(`MCP harvester failed: ${mcpError.message}. Falling back to direct Python execution.`);
      
      // Option 2: Direct Python execution
      return this.executeHarvesterDirect(params);
    }
  }

  private async executeHarvesterDirect(params: HarvesterParams): Promise<HarvesterResult[]> {
    this.logger.log('Attempting direct Python harvester execution.');
    const { spawn } = require('child_process');
    
    return new Promise((resolve, reject) => {
      const pythonArgs = [
        'prospect/harvester.py', // Path relative to CWD where NestJS app runs
        '--query', params.query,
        '--max-sites', params.maxSites.toString(),
        '--output-format', 'json' // Ensure harvester.py supports this and outputs JSON string
      ];
      this.logger.debug(`Spawning Python process: python ${pythonArgs.join(' ')}`);

      const pythonProcess = spawn('python3', pythonArgs); // Using python3 explicitly

      let output = '';
      let errorOutput = '';

      pythonProcess.stdout.on('data', (data: Buffer) => {
        output += data.toString();
      });

      pythonProcess.stderr.on('data', (data: Buffer) => {
        errorOutput += data.toString();
        this.logger.error(`Harvester stderr: ${data.toString()}`);
      });

      pythonProcess.on('close', (code: number) => {
        this.logger.log(`Python harvester process exited with code ${code}.`);
        if (errorOutput && code !== 0) {
           this.logger.error(`Python harvester errors: ${errorOutput}`);
        }

        if (code === 0) {
          try {
            // Assuming harvester.py prints a JSON array of HarvesterResult objects to stdout
            const results = JSON.parse(output); 
            this.logger.log(`Successfully parsed ${results?.length || 0} results from direct harvester.`);
            resolve(results || []); // Ensure it's an array
          } catch (parseError) {
            this.logger.error(`Failed to parse harvester output: ${parseError.message}. Output was: ${output}`);
            reject(new Error(`Failed to parse harvester output: ${parseError.message}`));
          }
        } else {
          reject(new Error(`Harvester process failed with code ${code}. Error: ${errorOutput || 'Unknown error'}`));
        }
      });

      pythonProcess.on('error', (err) => {
        this.logger.error(`Failed to start Python harvester process: ${err.message}`);
        reject(new Error(`Failed to start harvester process: ${err.message}`));
      });
    });
  }

  private async processHarvesterResults(
    results: HarvesterResult[], 
    context: BusinessContextType
  ): Promise<CreateLeadDto[]> {
    this.logger.debug(`Processing ${results.length} harvester results.`);
    const processedLeads: CreateLeadDto[] = [];

    for (const result of results) {
      if (!result || !result.url) {
        this.logger.warn('Skipping invalid harvester result (missing URL).');
        continue;
      }
      try {
        this.logger.debug(`Processing result for URL: ${result.url}`);
        // Ensure mcpService.processRawDataToLead is correctly typed and implemented
        const leadData = await this.mcpService.processRawDataToLead(result, context);
        if (leadData) {
          this.logger.debug(`Successfully processed data for ${result.url} into lead DTO.`);
          processedLeads.push(leadData);
        } else {
          this.logger.warn(`MCP service returned no lead data for ${result.url}.`);
        }
      } catch (error) {
        this.logger.warn(`Failed to process result for ${result.url} via MCP: ${error.message}`);
      }
    }
    this.logger.log(`Finished processing harvester results. ${processedLeads.length} leads ready for saving.`);
    return processedLeads;
  }

  private async saveLeadsToDatabase(leads: CreateLeadDto[]): Promise<LeadData[]> {
    this.logger.debug(`Saving ${leads.length} leads to database.`);
    const savedLeads: LeadData[] = [];

    for (const leadDto of leads) {
      try {
        // Ensure leadsService.create is correctly typed and implemented
        const savedLead = await this.leadsService.create(leadDto);
        this.logger.debug(`Saved lead: ${savedLead.company_name} (ID: ${savedLead.id})`);
        savedLeads.push(savedLead);
      } catch (error) {
        this.logger.warn(`Failed to save lead for ${leadDto.company_name}: ${error.message}`);
      }
    }
    this.logger.log(`Finished saving leads. ${savedLeads.length} leads saved.`);
    return savedLeads;
  }
}
