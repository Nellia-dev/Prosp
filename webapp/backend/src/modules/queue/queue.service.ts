import { Injectable, Logger } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bull';
import { Queue } from 'bull';
import { ProcessingStage } from '../../shared/types/nellia.types';

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
  ) {}

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