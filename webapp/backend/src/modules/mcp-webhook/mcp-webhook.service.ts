import { Injectable, Logger } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bull';
import { Queue } from 'bull';
import { LeadsService } from '../leads/leads.service';
import { QuotaService } from '../quota/quota.service';
import { UsersService } from '../users/users.service';
import { WebSocketService } from '../websocket/websocket.service';
import { CreateLeadDto, LeadData } from '../../shared/types/nellia.types';
import { JobCompletedData, JobFailedData, QuotaUpdateData, JobProgressData } from '../websocket/dto/websocket.dto';
import { LeadStatus } from '@/shared/enums/nellia.enums';
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

  async processCompletedJob(payload: WebhookPayload): Promise<void> {
    const { job_id, user_id, status, data } = payload;
    this.logger.log(`Processing webhook for completed job ${job_id} for user ${user_id}`);

    try {
      if (status === 'failed' || !data.success) {
        const errorMessage = data.error_message || 'Unknown error during harvester execution.';
        this.logger.error(`Job ${job_id} failed: ${errorMessage}`);
        await this.handleFailedJob(user_id, job_id, errorMessage);
        return;
      }

      const leadsToCreate = (data.leads_data || []).map(lead => ({
        ...lead,
        userId: user_id,
      } as CreateLeadDto));

      this.logger.log(`Job ${job_id}: ${leadsToCreate.length} leads received from MCP.`);

      const createdLeads = await this.createLeadsAndDispatchForEnrichment(leadsToCreate, user_id, job_id);

      if (createdLeads.length > 0) {
        await this.quotaService.consumeQuota(user_id, createdLeads.length);
        this.logger.log(`Job ${job_id}: Consumed ${createdLeads.length} quota for user ${user_id}`);
      }

      await this.usersService.clearProspectingJob(user_id);
      await this.emitJobCompletedEvent(user_id, job_id, createdLeads.length, 'Agentic Search');

    } catch (error) {
      this.logger.error(`Error processing webhook for job ${job_id}: ${error.message}`, error.stack);
      await this.handleFailedJob(user_id, job_id, 'Internal error processing webhook.');
    }
  }

  async processStreamedEvent(event: any): Promise<void> {
    const { user_id, job_id, event_type, ...data } = event;

    if (!user_id) {
      this.logger.warn('Received a streamed event without a user_id. Cannot broadcast.');
      return;
    }

    this.logger.debug(`Processing streamed event [${event_type}] for job [${job_id}] for user [${user_id}]`);

    // Map Python event types to specific frontend WebSocket events
    switch (event_type) {
      case 'status_update':
        const progressData: JobProgressData = {
          jobId: job_id,
          userId: user_id,
          status: 'active',
          progress: data.progress || 50, // Default progress if not specified
          currentStep: data.status_message,
          timestamp: data.timestamp,
        };
        this.webSocketService.emitJobProgress(user_id, progressData);
        break;

      case 'agent_start':
      case 'agent_end':
      case 'pipeline_end':
      case 'pipeline_error':
        // These events are all related to the enrichment process status
        this.webSocketService.emitEnrichmentUpdate(user_id, event);
        break;

      default:
        this.logger.warn(`Unhandled event type received: ${event_type}`);
        // Optionally, send to a generic channel for debugging
        this.webSocketService.emitToUser(user_id, 'unhandled-pipeline-event', event);
        break;
    }
  }

  private async createLeadsAndDispatchForEnrichment(leads: CreateLeadDto[], userId: string, harvesterJobId: string): Promise<LeadData[]> {
    const createdLeads: LeadData[] = [];
    for (const leadDto of leads) {
      try {
        const newLead = await this.leadsService.create({ ...leadDto, status: LeadStatus.HARVESTED });
        await this.enrichmentQueue.add('enrich-lead', {
          leadId: newLead.id,
          userId: userId,
          jobId: harvesterJobId,
        });
        createdLeads.push(newLead);
      } catch (error) {
        this.logger.error(`Failed to create or dispatch lead for ${leadDto.company_name}: ${error.message}`, error.stack);
      }
    }
    return createdLeads;
  }

  private async handleFailedJob(userId: string, jobId: string, error: string): Promise<void> {
    await this.usersService.clearProspectingJob(userId);
    await this.emitJobFailedEvent(userId, jobId, error, 'Agentic Search');
  }

  private async emitJobCompletedEvent(userId: string, jobId: string, leadsGenerated: number, searchQuery: string): Promise<void> {
    const user = await this.usersService.getUserById(userId);
    const planDetails = PLANS[user.plan];
    const remainingQuota = await this.quotaService.getRemainingQuota(userId);
    const quotaUsed = planDetails.quota - remainingQuota;

    const quotaUpdate: QuotaUpdateData = {
      userId,
      planId: user.plan,
      planName: planDetails.name,
      quotaUsed,
      quotaTotal: planDetails.quota === Infinity ? 999999 : planDetails.quota,
      quotaRemaining: remainingQuota,
      quotaUsagePercentage: planDetails.quota === Infinity ? 0 : Math.round((quotaUsed / planDetails.quota) * 100),
      nextResetAt: this.calculateNextResetDate(user.lastQuotaResetAt, planDetails.period),
      leadsGenerated,
      timestamp: new Date().toISOString(),
    };

    const jobCompletedData: JobCompletedData = {
      jobId,
      userId,
      status: 'completed',
      leadsGenerated,
      searchQuery,
      quotaUpdate,
      startedAt: new Date().toISOString(), // Note: This is the completion time, not start.
      completedAt: new Date().toISOString(),
      timestamp: new Date().toISOString(),
    };

    this.webSocketService.emitJobCompleted(userId, jobCompletedData);
  }

  private async emitJobFailedEvent(userId: string, jobId: string, error: string, searchQuery: string): Promise<void> {
    const jobFailedData: JobFailedData = {
      jobId,
      userId,
      status: 'failed',
      error,
      searchQuery,
      startedAt: new Date().toISOString(), // Note: This is the failure time, not start.
      failedAt: new Date().toISOString(),
      timestamp: new Date().toISOString(),
    };
    this.webSocketService.emitJobFailed(userId, jobFailedData);
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