import { Processor, Process } from '@nestjs/bull';
import { Job } from 'bull';
import { Logger } from '@nestjs/common';
import { LeadsService } from '../../leads/leads.service';
import { McpService } from '../../mcp/mcp.service';
import { QueueService } from '../queue.service';
import { LeadStatus } from '@/shared/enums/nellia.enums';
import { BusinessContextService } from '@/modules/business-context/business-context.service';

interface EnrichmentJobData {
  leadId: string;
  userId: string;
  harvesterJobId: string; // The original job ID for context
}

@Processor('enrichment-processing')
export class EnrichmentProcessor {
  private readonly logger = new Logger(EnrichmentProcessor.name);

  constructor(
    private readonly leadsService: LeadsService,
    private readonly mcpService: McpService,
    private readonly queueService: QueueService,
    private readonly businessContextService: BusinessContextService,
  ) {
    this.logger.log('EnrichmentProcessor initialized and listening for jobs.');
  }

  @Process('enrich-lead')
  async handleEnrichmentProcess(job: Job<EnrichmentJobData>): Promise<any> {
    const { leadId, userId, harvesterJobId } = job.data;
    this.logger.log(`[ENRICH_START] Picked up job ${job.id} to enrich lead ${leadId} for user ${userId}.`);

    // Use findById to get the full Lead entity, not the LeadData DTO
    const lead = await this.leadsService.findById(leadId);
    if (!lead) {
      this.logger.error(`Lead with ID ${leadId} not found.`);
      throw new Error(`Lead not found: ${leadId}`);
    }
    
    // Ensure the lead belongs to the user who queued the job
    if (lead.userId !== userId) {
        this.logger.error(`User ${userId} does not have permission to enrich lead ${leadId}.`);
        throw new Error(`Permission denied for lead ${leadId}`);
    }

    try {
      await this.leadsService.updateStatus(leadId, LeadStatus.ENRICHING);

      const businessContext = await this.businessContextService.getContextForMcp(userId);
      const eventStream = await this.mcpService.executeUnifiedPipeline(businessContext, userId, harvesterJobId);

      for await (const event of eventStream) {
        // The queue service now has logic to parse and broadcast events
        await this.queueService.processStreamedEvent(event);
      }

      this.logger.log(`[ENRICH_SUCCESS] Successfully finished streaming enrichment for lead ${leadId}.`);
      
      // The final lead status update (e.g., to ENRICHED) will be handled
      // by the queue service when it receives the 'lead_enrichment_end' event.

      return { success: true, leadId, message: 'Enrichment stream completed.' };

    } catch (error) {
      this.logger.error(`Enrichment process failed for lead ${leadId}: ${error.message}`, error.stack);
      await this.leadsService.updateStatus(leadId, LeadStatus.ENRICHMENT_FAILED);
      // Optionally, emit a specific failure event via WebSocket
      await this.queueService.processStreamedEvent({
          event_type: 'pipeline_error',
          job_id: harvesterJobId,
          user_id: userId,
          lead_id: leadId,
          error_message: `Enrichment failed: ${error.message}`,
          error_type: error.constructor.name,
          timestamp: new Date().toISOString(),
      });
      throw error;
    }
  }
}
