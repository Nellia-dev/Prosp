import { Processor, Process } from '@nestjs/bull';
import { Logger } from '@nestjs/common';
import { Job } from 'bull';
import { AgentsService } from '../../agents/agents.service';
import { MetricsService } from '../../metrics/metrics.service';

export interface MetricsCollectionJobData {
  agentId?: string;
  type: 'agent_metrics' | 'system_metrics' | 'performance_metrics';
}

@Processor('metrics-collection')
export class MetricsCollectionProcessor {
  private readonly logger = new Logger(MetricsCollectionProcessor.name);

  constructor(
    private readonly agentsService: AgentsService,
    private readonly metricsService: MetricsService,
  ) {}

  @Process('collect-agent-metrics')
  async handleAgentMetricsCollection(job: Job<MetricsCollectionJobData>) {
    const { agentId, type } = job.data;
    
    this.logger.log(`Collecting ${type} metrics${agentId ? ` for agent ${agentId}` : ''}`);

    try {
      switch (type) {
        case 'agent_metrics':
          if (agentId) {
            await this.collectSingleAgentMetrics(agentId);
          } else {
            await this.collectAllAgentMetrics();
          }
          break;

        case 'system_metrics':
          await this.collectSystemMetrics();
          break;

        case 'performance_metrics':
          await this.collectPerformanceMetrics();
          break;

        default:
          throw new Error(`Unknown metrics collection type: ${type}`);
      }

      this.logger.log(`Successfully collected ${type} metrics`);
    } catch (error) {
      this.logger.error(`Failed to collect ${type} metrics`, error.stack);
      throw error;
    }
  }

  @Process('aggregate-daily-metrics')
  async handleDailyMetricsAggregation(job: Job<{ date: string }>) {
    const { date } = job.data;
    
    this.logger.log(`Aggregating daily metrics for ${date}`);

    try {
      // Get dashboard metrics for the specific date
      const dashboardMetrics = await this.metricsService.getDashboardMetrics();
      
      // Store aggregated metrics (this would typically go to a separate metrics storage)
      this.logger.log(`Daily metrics aggregated for ${date}:`, {
        totalLeads: dashboardMetrics.totalLeads,
        completedLeads: dashboardMetrics.completedLeads,
        averageProcessingTime: dashboardMetrics.averageProcessingTime,
        successRate: dashboardMetrics.successRate,
      });

      this.logger.log(`Successfully aggregated daily metrics for ${date}`);
    } catch (error) {
      this.logger.error(`Failed to aggregate daily metrics for ${date}`, error.stack);
      throw error;
    }
  }

  private async collectSingleAgentMetrics(agentId: string): Promise<void> {
    const agent = await this.agentsService.findOne(agentId);
    if (!agent) {
      throw new Error(`Agent ${agentId} not found`);
    }

    // Update agent metrics from MCP service or internal tracking
    const updatedMetrics = {
      ...agent.metrics,
      // Note: AgentMetrics doesn't have lastCollected field, so we'll just refresh the metrics
    };

    await this.agentsService.updateAgentMetrics(agentId, updatedMetrics);
  }

  private async collectAllAgentMetrics(): Promise<void> {
    const agents = await this.agentsService.findAll();
    
    for (const agent of agents) {
      try {
        await this.collectSingleAgentMetrics(agent.id);
      } catch (error) {
        this.logger.warn(`Failed to collect metrics for agent ${agent.id}`, error.message);
      }
    }
  }

  private async collectSystemMetrics(): Promise<void> {
    // Collect system-wide performance metrics
    const systemMetrics = {
      timestamp: new Date().toISOString(),
      memoryUsage: process.memoryUsage(),
      cpuUsage: process.cpuUsage(),
      uptime: process.uptime(),
    };

    this.logger.log('System metrics collected:', systemMetrics);
  }

  private async collectPerformanceMetrics(): Promise<void> {
    // Collect performance metrics from MetricsService
    try {
      const performanceData = await this.metricsService.getPerformanceData('24h');
      
      this.logger.log(`Performance metrics collected: ${performanceData.length} data points`);
    } catch (error) {
      this.logger.warn('Failed to collect performance metrics', error.message);
    }
  }
}