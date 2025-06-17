import { Injectable, Logger } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bull';
import { Queue } from 'bull';
import { ProcessingStage } from '../../shared/types/nellia.types';
import { WebSocketService } from '../websocket/websocket.service';
import { LeadsService } from '../leads/leads.service';
import { QuotaService } from '../quota/quota.service';
import { UsersService } from '../users/users.service';
import { CreateLeadDto } from '../../shared/types/nellia.types';
import { JobCompletedData, JobFailedData, QuotaUpdateData } from '../websocket/dto/websocket.dto';
import { LeadStatus } from '@/shared/enums/nellia.enums';
import { PLANS } from '../../config/plans.config';

@Injectable()
export class QueueService {
  private readonly logger = new Logger(QueueService.name);

  constructor(
    @InjectQueue('prospect-processing')
    private readonly prospectProcessingQueue: Queue,
    @InjectQueue('enrichment-processing')
    private readonly enrichmentProcessingQueue: Queue,
    @InjectQueue('metrics-collection')
    private readonly metricsQueue: Queue,
    @InjectQueue('cleanup')
    private readonly cleanupQueue: Queue,
    private readonly webSocketService: WebSocketService,
    private readonly leadsService: LeadsService,
    private readonly quotaService: QuotaService,
    private readonly usersService: UsersService,
  ) { }

  // ===================================
  // Lead Processing Queue Methods
  // ===================================

  async addProspectProcessingJob(leadId: string, stage: ProcessingStage, priority = 0): Promise<void> {
    await this.prospectProcessingQueue.add(
      'process-lead',
      {
        leadId,
        stage,
        retryCount: 0,
      },
      {
        priority,
        delay: 0,
      }
    );

    this.logger.log(`Added lead processing job for lead ${leadId} at stage ${stage}`);
  }

  async addBulkProspectProcessingJob(leadIds: string[], priority = 0): Promise<void> {
    await this.prospectProcessingQueue.add(
      'bulk-process-leads',
      {
        leadIds,
      },
      {
        priority,
      }
    );

    this.logger.log(`Added bulk processing job for ${leadIds.length} leads`);
  }

  // ===================================
  // Metrics Collection Queue Methods
  // ===================================

  async scheduleAgentMetricsCollection(agentId?: string): Promise<void> {
    await this.metricsQueue.add(
      'collect-agent-metrics',
      {
        agentId,
        type: 'agent_metrics',
      },
      {
        repeat: { cron: '*/15 * * * *' }, // Every 15 minutes
      }
    );

    this.logger.log(`Scheduled agent metrics collection${agentId ? ` for agent ${agentId}` : ''}`);
  }

  async scheduleSystemMetricsCollection(): Promise<void> {
    await this.metricsQueue.add(
      'collect-agent-metrics',
      {
        type: 'system_metrics',
      },
      {
        repeat: { cron: '*/5 * * * *' }, // Every 5 minutes
      }
    );

    this.logger.log('Scheduled system metrics collection');
  }

  async scheduleDailyMetricsAggregation(): Promise<void> {
    await this.metricsQueue.add(
      'aggregate-daily-metrics',
      {
        date: new Date().toISOString().split('T')[0],
      },
      {
        repeat: { cron: '0 1 * * *' }, // Daily at 1 AM
      }
    );

    this.logger.log('Scheduled daily metrics aggregation');
  }

  // ===================================
  // Cleanup Queue Methods
  // ===================================

  async scheduleDataCleanup(): Promise<void> {
    // Schedule various cleanup tasks
    const cleanupTasks = [
      { type: 'old_chat_messages', daysOld: 90 },
      { type: 'completed_jobs', daysOld: 7 },
      { type: 'temp_files', daysOld: 1 },
    ];

    for (const task of cleanupTasks) {
      await this.cleanupQueue.add(
        'cleanup-old-data',
        task,
        {
          repeat: { cron: '0 2 * * 0' }, // Weekly on Sunday at 2 AM
        }
      );
    }

    this.logger.log('Scheduled data cleanup tasks');
  }

  async scheduleDatabaseMaintenance(): Promise<void> {
    await this.cleanupQueue.add(
      'vacuum-database',
      {
        analyze: true,
      },
      {
        repeat: { cron: '0 3 * * 0' }, // Weekly on Sunday at 3 AM
      }
    );

    this.logger.log('Scheduled database maintenance');
  }

  async scheduleSessionCleanup(): Promise<void> {
    await this.cleanupQueue.add(
      'cleanup-expired-sessions',
      {},
      {
        repeat: { cron: '0 4 * * *' }, // Daily at 4 AM
      }
    );

    this.logger.log('Scheduled session cleanup');
  }

  // ===================================
  // Queue Management Methods
  // ===================================

  async getQueueStats(): Promise<{
    prospectProcessing: any;
    enrichmentProcessing: any;
    metricsCollection: any;
    cleanup: any;
  }> {
    const [prospectStats, enrichmentStats, metricsStats, cleanupStats] = await Promise.all([
      this.getQueueInfo(this.prospectProcessingQueue),
      this.getQueueInfo(this.enrichmentProcessingQueue),
      this.getQueueInfo(this.metricsQueue),
      this.getQueueInfo(this.cleanupQueue),
    ]);

    return {
      prospectProcessing: prospectStats,
      enrichmentProcessing: enrichmentStats,
      metricsCollection: metricsStats,
      cleanup: cleanupStats,
    };
  }

  private async getQueueInfo(queue: Queue): Promise<any> {
    const [waiting, active, completed, failed, delayed] = await Promise.all([
      queue.getWaiting(),
      queue.getActive(),
      queue.getCompleted(),
      queue.getFailed(),
      queue.getDelayed(),
    ]);

    return {
      name: queue.name,
      waiting: waiting.length,
      active: active.length,
      completed: completed.length,
      failed: failed.length,
      delayed: delayed.length,
    };
  }

  async pauseQueue(queueName: string): Promise<void> {
    const queue = this.getQueueByName(queueName);
    await queue.pause();
    this.logger.log(`Queue ${queueName} paused`);
  }

  async resumeQueue(queueName: string): Promise<void> {
    const queue = this.getQueueByName(queueName);
    await queue.resume();
    this.logger.log(`Queue ${queueName} resumed`);
  }

  async clearQueue(queueName: string): Promise<void> {
    const queue = this.getQueueByName(queueName);
    await queue.empty();
    this.logger.log(`Queue ${queueName} cleared`);
  }

  private getQueueByName(name: string): Queue {
    switch (name) {
      case 'prospect-processing':
        return this.prospectProcessingQueue;
      case 'enrichment-processing':
        return this.enrichmentProcessingQueue;
      case 'metrics-collection':
        return this.metricsQueue;
      case 'cleanup':
        return this.cleanupQueue;
      default:
        throw new Error(`Unknown queue: ${name}`);
    }
  }

  // ===================================
  // MCP Event Processing Methods (Migrated from MCP-Webhook)
  // ===================================

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

      case 'lead_enrichment_start':
        await this.handleLeadEnrichmentStart(user_id, job_id, data.lead_id, data.company_name);
        break;

      case 'lead_enrichment_end':
        await this.handleLeadEnrichmentEnd(user_id, job_id, data.lead_id, data.success, data.final_package, data.error_message);
        break;

      case 'pipeline_end':
        await this.handlePipelineEnd(user_id, job_id, data.total_leads_generated);
        break;

      case 'status_update':
        await this.handleStatusUpdate(user_id, job_id, data);
        break;

      case 'agent_start':
      case 'agent_end':
      case 'pipeline_error':
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

      // This is not needed here, the enrichment process starts automatically.
      // Dispatch for enrichment using the queue system
      // await this.enrichmentProcessingQueue.add('enrich-lead', {
      //   leadId: newLead.id,
      //   userId: userId,
      //   harvesterJobId: harvesterJobId,
      // });

      // Notify frontend of the new lead
      this.webSocketService.emitToUser(userId, 'lead-created', { lead: newLead });
      this.logger.log(`Successfully created lead ${newLead.id} and dispatched for enrichment.`);

    } catch (error) {
      this.logger.error(`Failed to create or dispatch lead for ${leadDto.company_name}: ${error.message}`, error.stack);
    }
  }

  private async handleLeadEnrichmentStart(userId: string, jobId: string, leadId: string, companyName: string): Promise<void> {
    try {
      // Update lead status to indicate enrichment has started
      await this.leadsService.updateStatus(leadId, LeadStatus.ENRICHING);
      await this.leadsService.updateStage(leadId, ProcessingStage.ANALYZING_REFINING);

      // Emit real-time update to frontend
      this.webSocketService.emitEnrichmentUpdate(userId, {
        event_type: 'lead_enrichment_start',
        job_id: jobId,
        lead_id: leadId,
        company_name: companyName,
        timestamp: new Date().toISOString(),
      });

      this.logger.log(`Enrichment started for lead ${leadId} (${companyName})`);
    } catch (error) {
      this.logger.error(`Error handling enrichment start for lead ${leadId}: ${error.message}`, error.stack);
    }
  }

  private async handleStatusUpdate(userId: string, jobId: string, data: any): Promise<void> {
    try {
      // Extract relevant information from the status update
      const { status_message, lead_id, agent_name, progress_percentage } = data;

      // If this status update is for a specific lead, update its processing stage
      if (lead_id) {
        // Map status messages to processing stages
        let newStage: ProcessingStage | null = null;

        if (status_message?.includes('qualification')) {
          newStage = ProcessingStage.LEAD_QUALIFICATION;
        } else if (status_message?.includes('analyzing') || status_message?.includes('analysis')) {
          newStage = ProcessingStage.ANALYZING_REFINING;
        } else if (status_message?.includes('strategy') || status_message?.includes('approach')) {
          newStage = ProcessingStage.POSSIBLY_QUALIFIED;
        }

        if (newStage) {
          await this.leadsService.updateStage(lead_id, newStage);
        }

        // Emit enrichment progress update
        this.webSocketService.emitEnrichmentUpdate(userId, {
          event_type: 'enrichment_progress',
          job_id: jobId,
          lead_id,
          current_agent: agent_name || 'AI Agent',
          status_message: status_message || 'Processing...',
          progress_percentage: progress_percentage || 50,
          timestamp: new Date().toISOString(),
        });
      } else {
        // General status update for the job
        this.webSocketService.emitEnrichmentUpdate(userId, {
          event_type: 'job_status_update',
          job_id: jobId,
          status_message: status_message || 'Pipeline processing...',
          timestamp: new Date().toISOString(),
        });
      }

      this.logger.debug(`Status update processed for job ${jobId}: ${status_message}`);
    } catch (error) {
      this.logger.error(`Error handling status update for job ${jobId}: ${error.message}`, error.stack);
    }
  }

  private async handleLeadEnrichmentEnd(userId: string, jobId: string, leadId: string, success: boolean, finalPackage: any, errorMessage?: string): Promise<void> {
    try {
      if (success && finalPackage) {
        // Use the specific update methods
        await this.leadsService.updateStatus(leadId, LeadStatus.ENRICHED);
        await this.leadsService.updateStage(leadId, ProcessingStage.COMPLETED);
        await this.leadsService.updateEnrichmentData(leadId, finalPackage);

        // Extract and save all relevant data from the final package
        const updateData: any = {};

        // Handle different package structures (enhanced vs hybrid)
        if (finalPackage.enhanced_strategy?.lead_qualification?.qualification_tier) {
          updateData.qualification_tier = finalPackage.enhanced_strategy.lead_qualification.qualification_tier;
        }

        // Extract scores from the top-level package
        if (finalPackage.relevance_score !== undefined) {
          updateData.relevance_score = finalPackage.relevance_score;
        }
        if (finalPackage.roi_potential_score !== undefined) {
          updateData.roi_potential_score = finalPackage.roi_potential_score;
        }

        // Extract analyzed lead data if available
        if (finalPackage.analyzed_lead) {
          const analyzedLead = finalPackage.analyzed_lead;

          if (analyzedLead.analysis?.company_sector) {
            updateData.company_sector = analyzedLead.analysis.company_sector;
          }

          // Extract pain points
          if (analyzedLead.analysis?.potential_challenges) {
            updateData.pain_point_analysis = analyzedLead.analysis.potential_challenges;
          }
        }

        // Extract persona information from top-level package
        if (finalPackage.persona_profile) {
          updateData.persona = {
            likely_role: finalPackage.persona_profile.persona_title || '',
            decision_maker_probability: finalPackage.persona_profile.decision_maker_likelihood || 0,
          };
        }

        // Extract purchase triggers from enhanced_strategy
        if (finalPackage.enhanced_strategy?.purchase_triggers) {
          updateData.purchase_triggers = finalPackage.enhanced_strategy.purchase_triggers;
        }

        // Extract AI intelligence data if available
        if (finalPackage.ai_intelligence) {
          // Store AI intelligence data in enrichment_data for full preservation
          const enrichmentData = finalPackage;
          enrichmentData.ai_intelligence_summary = {
            market_fit_score: finalPackage.ai_intelligence.pain_alignment_score,
            decision_maker_likelihood: finalPackage.ai_intelligence.buying_intent_score,
            lead_quality_score: finalPackage.ai_intelligence.prospect_score,
            recommended_approach: finalPackage.ai_intelligence.predictive_insights,
          };
        }

        // Update lead with extracted data
        if (Object.keys(updateData).length > 0) {
          await this.leadsService.update(leadId, updateData);
        }

        const updatedLead = await this.leadsService.findOne(leadId);
        this.webSocketService.emitToUser(userId, 'lead-enriched', { lead: updatedLead });
        this.logger.log(`Successfully enriched lead ${leadId} with comprehensive data extraction.`);
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

  // ===================================
  // Initialization
  // ===================================

  async initializeScheduledJobs(): Promise<void> {
    this.logger.log('Initializing scheduled queue jobs...');

    try {
      await Promise.all([
        this.scheduleAgentMetricsCollection(),
        this.scheduleSystemMetricsCollection(),
        this.scheduleDailyMetricsAggregation(),
        this.scheduleDataCleanup(),
        this.scheduleDatabaseMaintenance(),
        this.scheduleSessionCleanup(),
      ]);

      this.logger.log('All scheduled jobs initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize scheduled jobs', error.stack);
      throw error;
    }
  }
}
