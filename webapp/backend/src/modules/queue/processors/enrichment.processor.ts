import { Processor, Process, InjectQueue } from '@nestjs/bull';
import { Job, Queue } from 'bull';
import { Logger } from '@nestjs/common';
import { McpService } from '../../mcp/mcp.service';
import { LeadsService } from '../../leads/leads.service';
import { UsersService } from '../../users/users.service';
import { WebSocketService } from '../../websocket/websocket.service';
import { Lead } from '@/database/entities/lead.entity';
import { LeadStatus } from '@/shared/enums/nellia.enums';

export interface EnrichmentJobData {
  leadId: string;
  userId: string;
  jobId: string; // Original harvester job ID for tracking
}

@Processor('enrichment-processing')
export class EnrichmentProcessor {
  private readonly logger = new Logger(EnrichmentProcessor.name);

  constructor(
    private readonly mcpService: McpService,
    private readonly leadsService: LeadsService,
    private readonly usersService: UsersService,
    private readonly webSocketService: WebSocketService,
  ) {}

  @Process('enrich-lead')
  async handleEnrichmentProcess(job: Job<EnrichmentJobData>): Promise<any> {
    const { leadId, userId, jobId } = job.data;
    this.logger.log(`Starting enrichment for lead ${leadId} (Job: ${jobId})`);

    let lead: Lead;
    try {
      lead = await this.leadsService.findById(leadId);
      if (!lead) {
        throw new Error(`Lead with ID ${leadId} not found.`);
      }

      // 1. Update lead status to ENRICHING
      await this.leadsService.updateStatus(leadId, LeadStatus.ENRICHING);
      this.webSocketService.emitLeadUpdate(userId, {
        id: lead.id,
        status: LeadStatus.ENRICHING,
      });
      await job.progress(10);

      // 2. Call the MCP enrichment streaming endpoint
      const enrichmentStream = await this.mcpService.streamEnrichmentPipeline(lead, userId, jobId);

      let finalPackage = null;

      // 3. Process the event stream
      for await (const event of enrichmentStream) {
        // Emit real-time progress to the frontend
        this.webSocketService.emitEnrichmentUpdate(userId, event);

        if (event.event_type === 'agent_end' && event.data?.agent_name === 'EnhancedLeadProcessor') {
           if (event.data?.success) {
             finalPackage = event.data.final_response;
           }
        }
        
        if (event.event_type === 'pipeline_error') {
            throw new Error(event.data?.error_message || 'Unknown error during enrichment.');
        }
      }
      
      await job.progress(80);

      // 4. Update lead with the final package
      if (finalPackage) {
        await this.leadsService.updateEnrichmentData(leadId, finalPackage);
        this.logger.log(`Successfully enriched lead ${leadId} and saved package.`);
      } else {
        this.logger.warn(`Enrichment pipeline for lead ${leadId} finished without a final package.`);
      }

      // 5. Set final lead status
      await this.leadsService.updateStatus(leadId, LeadStatus.ENRICHED);
      this.webSocketService.emitLeadUpdate(userId, {
        id: lead.id,
        status: LeadStatus.ENRICHED,
        enrichment_data: finalPackage, // Send the full data on completion
      });
      
      await job.progress(100);
      this.logger.log(`Enrichment process completed for lead ${leadId}.`);

      return { success: true, leadId, message: 'Enrichment successful' };

    } catch (error) {
      this.logger.error(`Enrichment process failed for lead ${leadId}: ${error.message}`, error.stack);
      if (lead) {
        await this.leadsService.updateStatus(leadId, LeadStatus.ENRICHMENT_FAILED);
        this.webSocketService.emitLeadUpdate(userId, {
          id: lead.id,
          status: LeadStatus.ENRICHMENT_FAILED,
          error: error.message,
        });
      }
      await job.moveToFailed({ message: error.message }, true);
      throw error;
    }
  }
}