import { Processor, Process } from '@nestjs/bull';
import { Job } from 'bull';
import { Logger } from '@nestjs/common';
import { BusinessContextService } from '../../business-context/business-context.service';
import { LeadsService } from '../../leads/leads.service';
import { McpService } from '../../mcp/mcp.service';
import { UsersService } from '../../users/users.service';
import { QuotaService } from '../../quota/quota.service';
import { WebSocketService } from '../../websocket/websocket.service';
import { HarvesterJobData } from '../../prospect/prospect.service';
import { BusinessContext as BusinessContextType, CreateLeadDto, LeadData } from '../../../shared/types/nellia.types';
import { QuotaUpdateData, JobProgressData, JobCompletedData, JobFailedData } from '../../websocket/dto/websocket.dto';
import { PLANS } from '../../../config/plans.config';

interface HarvesterParams {
  query: string;
  maxSites: number;
  maxLeads: number; // New: quota-aware max leads
  context: BusinessContextType;
  userId: string; // Add userId to params
}

interface HarvesterResult {
  url: string;
  content_summary?: string;
  title?: string;
  [key: string]: any;
}

@Processor('prospect-processing')
export class ProspectProcessor {
  private readonly logger = new Logger(ProspectProcessor.name);

  constructor(
    private businessContextService: BusinessContextService,
    private leadsService: LeadsService,
    private mcpService: McpService,
    private usersService: UsersService,
    private quotaService: QuotaService,
    private webSocketService: WebSocketService,
  ) {}

  @Process('run-harvester')
  async handleHarvesterProcess(job: Job<HarvesterJobData>): Promise<any> {
    const { userId, searchQuery, maxSites, maxLeadsToReturn } = job.data;
    
    this.logger.log(`Starting harvester process for user ${userId}, job ${job.id}`);
    this.logger.log(`Job parameters: query="${searchQuery}", maxSites=${maxSites}, maxLeads=${maxLeadsToReturn}`);
    
    try {
      await job.progress(10);

      // Step 1: Validate user and quota
      const user = await this.usersService.getUserById(userId);
      const remainingQuota = await this.quotaService.getRemainingQuota(userId);
      
      if (remainingQuota <= 0) {
        throw new Error(`User ${userId} has no remaining quota for lead generation`);
      }

      this.logger.log(`User ${userId} has ${remainingQuota} leads remaining in quota`);
      await job.progress(20);

      // Step 2: Get business context
      const context = await this.businessContextService.getContextForMcp();
      if (!context) {
        throw new Error('Business context not found or not configured.');
      }
      
      this.logger.debug(`Job ${job.id}: Business context fetched for user ${userId}`);
      await job.progress(30);

      // Step 3: Build enhanced search query
      const enhancedQuery = this.buildSearchQuery(searchQuery, context);
      this.logger.debug(`Job ${job.id}: Enhanced search query: "${enhancedQuery}"`);
      await job.progress(40);

      // Step 4: Execute harvester with quota limits
      this.logger.log(`Job ${job.id}: Executing harvester for user ${userId} (query: "${enhancedQuery}", maxSites: ${maxSites}, maxLeads: ${maxLeadsToReturn})`);
      const harvesterResults = await this.executeHarvester({
        query: enhancedQuery,
        maxSites: maxSites,
        maxLeads: Math.min(maxLeadsToReturn, remainingQuota), // Respect both job limit and remaining quota
        context: context,
        userId: userId, // Add userId to params
      });
      
      this.logger.log(`Job ${job.id}: Harvester executed, found ${harvesterResults.length} results`);
      await job.progress(60);

      // Step 5: Process results through MCP agents
      this.logger.log(`Job ${job.id}: Processing ${harvesterResults.length} harvester results for user ${userId}`);
      const processedLeadsDto = await this.processHarvesterResults(harvesterResults, context, userId);
      
      // Limit leads to user's quota (safety check)
      const leadsToSave = processedLeadsDto.slice(0, Math.min(maxLeadsToReturn, remainingQuota));
      this.logger.log(`Job ${job.id}: ${leadsToSave.length} leads processed and ready for saving (limited by quota)`);
      await job.progress(80);

      // Step 6: Save leads to database with user association
      this.logger.log(`Job ${job.id}: Saving ${leadsToSave.length} leads for user ${userId}`);
      const savedLeads = await this.saveLeadsToDatabase(leadsToSave, userId);
      
      // Step 7: Consume quota for saved leads
      if (savedLeads.length > 0) {
        await this.quotaService.consumeQuota(userId, savedLeads.length);
        this.logger.log(`Job ${job.id}: Consumed ${savedLeads.length} quota for user ${userId}`);
      }
      
      // Step 8: Clear user's active job
      await this.usersService.clearProspectingJob(userId);
      
      await job.progress(100);

      const completionMessage = `Harvester process completed for user ${userId}, job ${job.id}. Saved ${savedLeads.length} leads, consumed ${savedLeads.length} quota.`;
      this.logger.log(completionMessage);

      // Step 9: Emit WebSocket events for job completion and quota update
      try {
        await this.emitJobCompletedEvent(userId, job.id.toString(), savedLeads.length, searchQuery);
        this.logger.log(`Job ${job.id}: WebSocket events emitted for user ${userId}`);
      } catch (wsError) {
        this.logger.warn(`Job ${job.id}: Failed to emit WebSocket events: ${wsError.message}`);
      }

      return {
        success: true,
        userId: userId,
        leadsCreated: savedLeads.length,
        quotaConsumed: savedLeads.length,
        jobId: job.id,
        message: completionMessage,
        completedAt: new Date().toISOString(),
      };

    } catch (error) {
      this.logger.error(`Harvester process failed for user ${userId}, job ${job.id}: ${error.message}`, error.stack);
      
      // Clear user's active job on failure
      try {
        await this.usersService.clearProspectingJob(userId);
      } catch (clearError) {
        this.logger.error(`Failed to clear job for user ${userId}: ${clearError.message}`);
      }

      // Emit job failed event
      try {
        await this.emitJobFailedEvent(userId, job.id.toString(), error.message, searchQuery);
        this.logger.log(`Job ${job.id}: Job failed WebSocket event emitted for user ${userId}`);
      } catch (wsError) {
        this.logger.warn(`Job ${job.id}: Failed to emit job failed WebSocket event: ${wsError.message}`);
      }
      
      await job.moveToFailed({ message: error.message }, true);
      throw error;
    }
  }

  private buildSearchQuery(baseQuery: string, context: BusinessContextType): string {
    const industryTerms = context.industry_focus?.join(' OR ') || '';
    const targetMarket = context.target_market || '';
    
    let query = baseQuery;
    if (industryTerms) query += ` (${industryTerms})`;
    if (targetMarket) query += ` ${targetMarket}`;
    
    return query.trim();
  }

  private async executeHarvester(params: HarvesterParams): Promise<HarvesterResult[]> {
    this.logger.debug(`Executing harvester with quota-aware params: ${JSON.stringify({
      query: params.query, 
      maxSites: params.maxSites,
      maxLeads: params.maxLeads
    })}`);
    
    // Option 1: Call via MCP (preferred)
    try {
      this.logger.log('Attempting harvester execution via MCP.');
      const mcpResults = await this.mcpService.runHarvester(
        params.query, 
        params.maxSites, 
        params.context,
        params.maxLeads,  // Pass quota limit to MCP
        params.userId // Pass userId for logging/context
      );
      this.logger.log(`MCP harvester successful, ${mcpResults?.length || 0} results.`);
      
      // MCP should already limit results, but add safety check
      const limitedResults = (mcpResults || []).slice(0, params.maxLeads);
      this.logger.log(`Limited results to ${limitedResults.length} based on quota`);
      
      return limitedResults;
    } catch (mcpError) {
      this.logger.warn(`MCP harvester failed: ${mcpError.message}. Falling back to direct Python execution.`);
      return this.executeHarvesterDirect(params);
    }
  }

  private async executeHarvesterDirect(params: HarvesterParams): Promise<HarvesterResult[]> {
    this.logger.log('Attempting direct Python harvester execution with quota limits.');
    const { spawn } = require('child_process');
    
    return new Promise((resolve, reject) => {
      const pythonArgs = [
        'prospect/harvester.py',
        '--query', params.query,
        '--max-sites', params.maxSites.toString(),
        '--max-leads', params.maxLeads.toString(), // Pass quota limit to Python
        '--output-format', 'json'
      ];
      
      this.logger.debug(`Spawning Python process: python3 ${pythonArgs.join(' ')}`);

      const pythonProcess = spawn('python3', pythonArgs);
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
        
        if (code === 0) {
          try {
            const results = JSON.parse(output);
            // Additional safety: limit results to maxLeads
            const limitedResults = (results || []).slice(0, params.maxLeads);
            this.logger.log(`Successfully parsed and limited to ${limitedResults.length} results from direct harvester.`);
            resolve(limitedResults);
          } catch (parseError) {
            this.logger.error(`Failed to parse harvester output: ${parseError.message}. Output: ${output}`);
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
    context: BusinessContextType,
    userId: string
  ): Promise<CreateLeadDto[]> {
    this.logger.debug(`Processing ${results.length} harvester results for user ${userId}.`);
    const processedLeads: CreateLeadDto[] = [];

    for (const result of results) {
      if (!result || !result.url) {
        this.logger.warn('Skipping invalid harvester result (missing URL).');
        continue;
      }
      
      try {
        this.logger.debug(`Processing result for URL: ${result.url}`);
        const leadData = await this.mcpService.processRawDataToLead(result, context);
        
        if (leadData) {
          // Add userId to the lead DTO
          const leadWithUser: CreateLeadDto = {
            ...leadData,
            userId: userId,
          };
          
          this.logger.debug(`Successfully processed data for ${result.url} into lead DTO for user ${userId}.`);
          processedLeads.push(leadWithUser);
        } else {
          this.logger.warn(`MCP service returned no lead data for ${result.url}.`);
        }
      } catch (error) {
        this.logger.warn(`Failed to process result for ${result.url} via MCP: ${error.message}`);
      }
    }
    
    this.logger.log(`Finished processing harvester results for user ${userId}. ${processedLeads.length} leads ready for saving.`);
    return processedLeads;
  }

  private async saveLeadsToDatabase(leads: CreateLeadDto[], userId: string): Promise<LeadData[]> {
    this.logger.debug(`Saving ${leads.length} leads to database for user ${userId}.`);
    const savedLeads: LeadData[] = [];

    for (const leadDto of leads) {
      try {
        const savedLead = await this.leadsService.create(leadDto);
        this.logger.debug(`Saved lead: ${savedLead.company_name} (ID: ${savedLead.id}) for user ${userId}`);
        savedLeads.push(savedLead);
      } catch (error) {
        this.logger.warn(`Failed to save lead for ${leadDto.company_name}: ${error.message}`);
      }
    }
    
    this.logger.log(`Finished saving leads for user ${userId}. ${savedLeads.length} leads saved.`);
    return savedLeads;
  }

  // WebSocket event emission methods
  private async emitJobCompletedEvent(
    userId: string, 
    jobId: string, 
    leadsGenerated: number, 
    searchQuery: string
  ): Promise<void> {
    try {
      // Get updated user and quota information
      const user = await this.usersService.getUserById(userId);
      const planDetails = PLANS[user.plan];
      const remainingQuota = await this.quotaService.getRemainingQuota(userId);
      const quotaUsed = planDetails.quota - remainingQuota;
      
      // Create quota update data
      const quotaUpdate: QuotaUpdateData = {
        userId: userId,
        planId: user.plan,
        planName: planDetails.name,
        quotaUsed: quotaUsed,
        quotaTotal: planDetails.quota === Infinity ? 999999 : planDetails.quota,
        quotaRemaining: remainingQuota,
        quotaUsagePercentage: planDetails.quota === Infinity 
          ? 0 
          : Math.round((quotaUsed / planDetails.quota) * 100),
        nextResetAt: this.calculateNextResetDate(user.lastQuotaResetAt, planDetails.period),
        leadsGenerated: leadsGenerated,
        timestamp: new Date().toISOString(),
      };

      // Create job completed data
      const jobCompletedData: JobCompletedData = {
        jobId: jobId,
        userId: userId,
        status: 'completed',
        leadsGenerated: leadsGenerated,
        searchQuery: searchQuery,
        quotaUpdate: quotaUpdate,
        startedAt: new Date().toISOString(), // This could be tracked more precisely
        completedAt: new Date().toISOString(),
        timestamp: new Date().toISOString(),
      };

      // Emit job completed event (includes quota update)
      this.webSocketService.emitJobCompleted(userId, jobCompletedData);
      
      this.logger.debug(`Job completed WebSocket event emitted for user ${userId}, job ${jobId}`);
    } catch (error) {
      this.logger.error(`Failed to emit job completed event: ${error.message}`, error.stack);
      throw error;
    }
  }

  private async emitJobFailedEvent(
    userId: string,
    jobId: string,
    error: string,
    searchQuery: string
  ): Promise<void> {
    try {
      const jobFailedData: JobFailedData = {
        jobId: jobId,
        userId: userId,
        status: 'failed',
        error: error,
        searchQuery: searchQuery,
        startedAt: new Date().toISOString(), // This could be tracked more precisely
        failedAt: new Date().toISOString(),
        timestamp: new Date().toISOString(),
      };

      this.webSocketService.emitJobFailed(userId, jobFailedData);
      
      this.logger.debug(`Job failed WebSocket event emitted for user ${userId}, job ${jobId}`);
    } catch (wsError) {
      this.logger.error(`Failed to emit job failed event: ${wsError.message}`, wsError.stack);
      // Don't throw here as this is secondary to the main error
    }
  }

  private calculateNextResetDate(lastResetAt: Date, period: 'day' | 'week' | 'month'): string {
    const lastReset = new Date(lastResetAt);
    const nextReset = new Date(lastReset);
    
    switch (period) {
      case 'day':
        nextReset.setDate(nextReset.getDate() + 1);
        break;
      case 'week':
        nextReset.setDate(nextReset.getDate() + 7);
        break;
      case 'month':
        nextReset.setMonth(nextReset.getMonth() + 1);
        break;
    }
    
    return nextReset.toISOString();
  }
}
