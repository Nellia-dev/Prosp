import { Processor, Process, InjectQueue } from '@nestjs/bull';
import { Job, Queue } from 'bull';
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
import { LeadStatus } from '@/shared/enums/nellia.enums';

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
    @InjectQueue('enrichment-processing') private readonly enrichmentQueue: Queue,
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
      const context = await this.businessContextService.getContextForMcp(userId);
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
      // Step 4: Dispatch job to MCP via McpService
      this.logger.log(`Job ${job.id}: Dispatching to MCP for user ${userId} (query: "${enhancedQuery}", maxSites: ${maxSites}, maxLeads: ${maxLeadsToReturn})`);
      
      const mcpResponse = await this.mcpService.runHarvester(
        enhancedQuery,
        maxSites,
        context,
        Math.min(maxLeadsToReturn, remainingQuota), // Respect both job limit and remaining quota
        userId,
      );

      await job.progress(100);

      const completionMessage = `Harvester job ${job.id} successfully dispatched to MCP. MCP Job ID: ${mcpResponse.job_id}. Waiting for webhook.`;
      this.logger.log(completionMessage);

      // The processor's job is now done. It has successfully handed off the task.
      // The McpWebhookService will handle the results when they arrive.
      return {
        success: true,
        userId: userId,
        jobId: job.id,
        mcpJobId: mcpResponse.job_id,
        message: completionMessage,
        dispatchedAt: new Date().toISOString(),
      };

    } catch (error) {
      this.logger.error(`Harvester process failed for user ${userId}, job ${job.id}: ${error.message}`, error.stack);
      
      // Clear user's active job on failure
      try {
        await this.usersService.clearProspectingJob(userId);
      } catch (clearError) {
        this.logger.error(`Failed to clear job for user ${userId}: ${clearError.message}`);
      }

      // The job failed to dispatch. The webhook service will not be called.
      // We should emit a generic failure event here to notify the user.
      this.webSocketService.emitJobFailed(userId, {
        jobId: job.id.toString(),
        userId: userId,
        status: 'failed',
        error: `Failed to dispatch job to MCP: ${error.message}`,
        searchQuery: searchQuery,
        startedAt: new Date(job.timestamp).toISOString(),
        failedAt: new Date().toISOString(),
        timestamp: new Date().toISOString(),
      });
      
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

}
