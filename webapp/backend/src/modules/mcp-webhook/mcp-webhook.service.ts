import { Injectable, Logger } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bull';
import { Queue } from 'bull';
import { LeadsService } from '../leads/leads.service';
import { QuotaService } from '../quota/quota.service';
import { UsersService } from '../users/users.service';
import { WebSocketService } from '../websocket/websocket.service';
import { CreateLeadDto, LeadData } from '../../shared/types/nellia.types';
import { JobCompletedData, JobFailedData, QuotaUpdateData, JobProgressData } from '../websocket/dto/websocket.dto';
import { LeadStatus, ProcessingStage } from '@/shared/enums/nellia.enums';
import { PLANS } from '../../config/plans.config';

export interface WebhookPayload {
  job_id: string;
  user_id: string;
  status: 'completed' | 'failed';
  data: {
    success: boolean;
    total_leads_generated: number;
    execution_time_seconds: number;
    error_message?: string;
    leads_data?: any[];
  };
}

@Injectable()
export class McpWebhookService {
  private readonly logger = new Logger(McpWebhookService.name);

  constructor(
    @InjectQueue('enrichment-processing') private readonly enrichmentQueue: Queue,
    private readonly leadsService: LeadsService,
    private readonly quotaService: QuotaService,
    private readonly usersService: UsersService,
    private readonly webSocketService: WebSocketService,
  ) {}

  async processStreamedEvent(event: any): Promise<void> {
    const { user_id, job_id, event_type, ...data } = event;

    if (!user_id) {
      this.logger.warn('Received a streamed event without a user_id. Cannot broadcast.');
      return;
    }

    this.logger.debug(`Processing streamed event [${event_type}] for job [${job_id}] for user [${user_id}]`);

    // Map Python event types to specific frontend WebSocket events
    switch (event_type) {
      case 'lead_generated':
        await this.handleLeadGenerated(user_id, job_id, data.lead_id, data.lead_data);
        break;

      case 'lead_enrichment_end':
        await this.handleLeadEnrichmentEnd(user_id, job_id, data.lead_id, data.success, data.final_package, data.error_message);
        break;
        
      case 'pipeline_end':
        await this.handlePipelineEnd(user_id, job_id, data.total_leads_generated);
        break;

      case 'status_update':
      case 'agent_start':
      case 'agent_end':
      case 'pipeline_error':
      case 'lead_enrichment_start':
        // These events are all related to the enrichment process status and are broadcasted to the user
        this.webSocketService.emitEnrichmentUpdate(user_id, event);
        break;

      default:
        this.logger.warn(`Unhandled event type received: ${event_type}`);
        this.webSocketService.emitToUser(user_id, 'unhandled-pipeline-event', event);
        break;
    }
  }

  private async handleLeadGenerated(userId: string, harvesterJobId: string, leadId: string, leadDto: CreateLeadDto): Promise<void> {
    try {
      const createDto = { ...leadDto, id: leadId, userId, status: LeadStatus.HARVESTED };
      const newLead = await this.leadsService.create(createDto);
      
      // Dispatch for enrichment
      await this.enrichmentQueue.add('enrich-lead', {
        leadId: newLead.id,
        userId: userId,
        harvesterJobId: harvesterJobId,
      });

      // Notify frontend of the new lead
      this.webSocketService.emitToUser(userId, 'lead-created', { lead: newLead });
      this.logger.log(`Successfully created lead ${newLead.id} and dispatched for enrichment.`);

    } catch (error) {
      this.logger.error(`Failed to create or dispatch lead for ${leadDto.company_name}: ${error.message}`, error.stack);
    }
  }

  private async handleLeadEnrichmentEnd(userId: string, jobId: string, leadId: string, success: boolean, finalPackage: any, errorMessage?: string): Promise<void> {
    try {
      if (success && finalPackage) {
        // Use the specific update methods
        await this.leadsService.updateStatus(leadId, LeadStatus.ENRICHED);
        await this.leadsService.updateStage(leadId, ProcessingStage.COMPLETED);
        await this.leadsService.updateEnrichmentData(leadId, finalPackage);
        await this.leadsService.update(leadId, {
          qualification_tier: finalPackage.enhanced_strategy?.lead_qualification?.qualification_tier,
        });

        const updatedLead = await this.leadsService.findOne(leadId);
        this.webSocketService.emitToUser(userId, 'lead-enriched', { lead: updatedLead });
        this.logger.log(`Successfully enriched lead ${leadId}.`);
      } else {
        await this.leadsService.updateStatus(leadId, LeadStatus.ENRICHMENT_FAILED);
        this.webSocketService.emitToUser(userId, 'lead_enrichment_failed', { leadId, error: errorMessage });
        this.logger.error(`Enrichment failed for lead ${leadId}: ${errorMessage}`);
      }
    } catch (error) {
      this.logger.error(`Error finalizing enrichment for lead ${leadId}: ${error.message}`, error.stack);
    }
  }

  private async handlePipelineEnd(userId: string, jobId: string, totalLeads: number): Promise<void> {
    try {
      await this.usersService.clearProspectingJob(userId);
      
      const user = await this.usersService.getUserById(userId);
      const planDetails = PLANS[user.plan];
      const quotaRemaining = await this.quotaService.getRemainingQuota(userId);
      const quotaUsed = planDetails.quota - quotaRemaining;

      const quotaUpdate: QuotaUpdateData = {
        userId,
        planId: user.plan,
        planName: planDetails.name,
        quotaUsed,
        quotaTotal: planDetails.quota === Infinity ? 999999 : planDetails.quota,
        quotaRemaining: quotaRemaining,
        quotaUsagePercentage: planDetails.quota === Infinity ? 0 : Math.round((quotaUsed / planDetails.quota) * 100),
        nextResetAt: this.calculateNextResetDate(user.lastQuotaResetAt, planDetails.period),
        leadsGenerated: totalLeads,
        timestamp: new Date().toISOString(),
      };

      const jobCompletedData: JobCompletedData = {
        jobId,
        userId,
        status: 'completed',
        leadsGenerated: totalLeads,
        searchQuery: 'Context-driven Search',
        quotaUpdate,
        startedAt: new Date().toISOString(), // This should be improved to use actual start time
        completedAt: new Date().toISOString(),
        timestamp: new Date().toISOString(),
      };

      this.webSocketService.emitJobCompleted(userId, jobCompletedData);
      this.logger.log(`Prospecting job ${jobId} officially completed for user ${userId}.`);

    } catch (error) {
      this.logger.error(`Error handling pipeline end for job ${jobId}: ${error.message}`, error.stack);
    }
  }

  private calculateNextResetDate(lastResetAt: Date, period: 'day' | 'week' | 'month'): string {
    const lastReset = new Date(lastResetAt);
    const nextReset = new Date(lastReset);
    switch (period) {
      case 'day': nextReset.setDate(nextReset.getDate() + 1); break;
      case 'week': nextReset.setDate(nextReset.getDate() + 7); break;
      case 'month': nextReset.setMonth(nextReset.getMonth() + 1); break;
    }
    return nextReset.toISOString();
  }
}