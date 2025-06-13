import { Processor, Process, InjectQueue } from '@nestjs/bull';
import { Job, Queue } from 'bull';
import { Logger } from '@nestjs/common';
import { BusinessContextService } from '../../business-context/business-context.service';
import { LeadsService } from '../../leads/leads.service';
import { McpService } from '../../mcp/mcp.service';
import { QueueService } from '../queue.service';
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
    private readonly businessContextService: BusinessContextService,
    private readonly leadsService: LeadsService,
    private readonly mcpService: McpService,
    private readonly usersService: UsersService,
    private readonly quotaService: QuotaService,
    private readonly webSocketService: WebSocketService,
    private readonly queueService: QueueService,
  ) {
    this.logger.log('ProspectProcessor initialized. Listening for jobs on "prospect-processing" queue.');
  }

  @Process('start-unified-pipeline')
  async handleUnifiedPipeline(job: Job<HarvesterJobData>): Promise<any> {
    this.logger.log(`[JOB_START] Picked up job ${job.id} with name ${job.name}`);
    const { userId, businessContext } = job.data;
    
    this.logger.log(`[JOB_DATA] Starting unified pipeline for user ${userId}, job ${job.id}`);
    
    try {
      await job.progress(5);

      // The MCP service will now handle the entire streaming pipeline
      this.logger.log(`Job ${job.id}: Dispatching to MCP service to start unified pipeline.`);
      
      const eventStream = await this.mcpService.executeUnifiedPipeline(
        businessContext,
        userId,
        job.id.toString(),
      );

      // The processor's main job is to consume the event stream and pass events
      // to the webhook service, which contains the logic for handling each event type.
      for await (const event of eventStream) {
        await this.queueService.processStreamedEvent(event);
      }

      await job.progress(100);
      this.logger.log(`[JOB_SUCCESS] Unified pipeline stream completed for job ${job.id}.`);

      // The 'pipeline_end' event from the stream will trigger the final user notification.
      return {
        success: true,
        jobId: job.id,
        message: 'Unified pipeline stream processed successfully.',
      };

    } catch (error) {
      this.logger.error(`Unified pipeline failed for user ${userId}, job ${job.id}: ${error.message}`, error.stack);
      
      try {
        await this.usersService.clearProspectingJob(userId);
      } catch (clearError) {
        this.logger.error(`Failed to clear job for user ${userId}: ${clearError.message}`);
      }

      this.webSocketService.emitJobFailed(userId, {
        jobId: job.id.toString(),
        userId: userId,
        status: 'failed',
        error: `Pipeline execution failed: ${error.message}`,
        searchQuery: 'Context-driven search',
        startedAt: new Date(job.timestamp).toISOString(),
        failedAt: new Date().toISOString(),
        timestamp: new Date().toISOString(),
      });
      
      await job.moveToFailed({ message: error.message }, true);
      throw error;
    }
  }


}
