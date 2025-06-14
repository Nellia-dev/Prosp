import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Agent } from '../../database/entities/agent.entity';
import { Lead } from '../../database/entities/lead.entity';
import { ProcessingStage } from '../../shared/enums/nellia.enums';
import { ChatMessage } from '../../database/entities/chat-message.entity';
import {
  DashboardMetricsResponse, // Updated
  RecentActivityItem, // Added
  AgentPerformanceData,
  PerformanceDataPoint,
  MetricsPeriod,
  AgentMetrics,
} from '../../shared/types/nellia.types';
import { AgentStatus as AgentStatusEnum } from '../../database/entities/agent.entity'; // Added for activeAgents

@Injectable()
export class MetricsService {
  private readonly logger = new Logger(MetricsService.name);

  constructor(
    @InjectRepository(Agent)
    private readonly agentRepository: Repository<Agent>,
    @InjectRepository(Lead)
    private readonly leadRepository: Repository<Lead>,
    @InjectRepository(ChatMessage)
    private readonly chatMessageRepository: Repository<ChatMessage>,
  ) {}

  /**
   * Get comprehensive dashboard metrics
   */
  async getDashboardMetrics(): Promise<DashboardMetricsResponse> {
    try {
      const [
        totalLeads,
        completedLeads, // Used for successRate calculation
        totalAgents,
        activeAgents,
        // processingRate will be a placeholder for now
        // recentActivity will be a placeholder for now
      ] = await Promise.all([
        this.getTotalLeadsCount(),
        this.getCompletedLeadsCount(),
        this.getTotalAgentsCount(),
        this.getActiveAgentsCount(),
      ]);

      const successRate = totalLeads > 0 ? (completedLeads / totalLeads) * 100 : 0;
      const processingRate = 0; // Placeholder
      const recentActivity: RecentActivityItem[] = []; // Placeholder

      return {
        totalLeads,
        totalAgents,
        activeAgents,
        processingRate,
        successRate: parseFloat(successRate.toFixed(2)),
        recentActivity,
        lastUpdated: new Date(),
      };
    } catch (error) {
      this.logger.error('Failed to get dashboard metrics', error.stack);
      return this.getDefaultDashboardMetrics();
    }
  }

  /**
   * Get default metrics when none exist or errors occur
   */
  private getDefaultDashboardMetrics(): DashboardMetricsResponse {
    return {
      totalLeads: 0,
      totalAgents: 0,
      activeAgents: 0,
      processingRate: 0,
      successRate: 0,
      recentActivity: [],
      lastUpdated: new Date(),
    };
  }

  /**
   * Get performance data over time for charts
   */
  async getPerformanceData(period: MetricsPeriod = '7d'): Promise<PerformanceDataPoint[]> {
    try {
      const days = this.getPeriodDays(period);
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);

      const query = this.leadRepository.createQueryBuilder('lead')
        .select("DATE(lead.created_at)", "date")
        .addSelect("COUNT(*)", "throughput")
        .addSelect("AVG(EXTRACT(EPOCH FROM (lead.updated_at - lead.created_at)))", "avgProcessingTime")
        .where("lead.created_at >= :startDate", { startDate })
        .groupBy("DATE(lead.created_at)")
        .orderBy("date", "ASC");

      const rawData = await query.getRawMany();

      return rawData.map(item => ({
        date: new Date(item.date).toISOString().split('T')[0],
        throughput: parseInt(item.throughput, 10),
        processingTime: parseFloat(item.avgProcessingTime) || 0,
      }));
    } catch (error) {
      this.logger.error('Failed to get performance data', error.stack);
      throw new Error('Failed to retrieve performance data');
    }
  }

  /**
   * Get agent performance data for comparison charts
   */
  async getAgentPerformanceData(): Promise<AgentPerformanceData[]> {
    try {
      const agents = await this.agentRepository.find();
      
      const performanceData: AgentPerformanceData[] = [];

      for (const agent of agents) {
        const [successCount, errorCount, avgProcessingTime] = await Promise.all([
          this.getAgentSuccessCount(agent.id),
          this.getAgentErrorCount(agent.id),
          this.getAgentAverageProcessingTime(agent.id),
        ]);

        performanceData.push({
          agentName: agent.name,
          success: successCount,
          errors: errorCount,
          avgProcessingTime,
        });
      }

      return performanceData;
    } catch (error) {
      this.logger.error('Failed to get agent performance data', error.stack);
      throw new Error('Failed to retrieve agent performance data');
    }
  }

  /**
   * Get metrics for a specific agent
   */
  async getAgentMetrics(agentId?: string): Promise<AgentMetrics[]> {
    try {
      let agents: Agent[];
      
      if (agentId) {
        const agent = await this.agentRepository.findOne({ where: { id: agentId } });
        agents = agent ? [agent] : [];
      } else {
        agents = await this.agentRepository.find();
      }

      const metricsPromises = agents.map(async (agent) => {
        const [
          processingTime,
          successRate,
          queueDepth,
          throughput,
          tokenUsage,
        ] = await Promise.all([
          this.getAgentAverageProcessingTime(agent.id),
          this.getAgentSuccessRate(agent.id),
          this.getAgentQueueDepth(agent.id),
          this.getAgentThroughput(agent.id),
          this.getAgentTokenUsage(agent.id),
        ]);

        return {
          processing_time_seconds: processingTime,
          success_rate: successRate,
          queue_depth: queueDepth,
          throughput_per_hour: throughput,
          llm_usage: {
            total_tokens: tokenUsage,
            prompt_tokens: Math.floor(tokenUsage * 0.7), // Estimate
            completion_tokens: Math.floor(tokenUsage * 0.3), // Estimate
          },
        } as AgentMetrics;
      });

      return await Promise.all(metricsPromises);
    } catch (error) {
      this.logger.error('Failed to get agent metrics', error.stack);
      throw new Error('Failed to retrieve agent metrics');
    }
  }

  /**
   * Get lead statistics by stage
   */
  async getLeadStatsByStage() {
    try {
      const stats = await this.leadRepository
        .createQueryBuilder('lead')
        .select('lead.processing_stage', 'stage')
        .addSelect('COUNT(*)', 'count')
        .addSelect('AVG(lead.roi_potential_score)', 'avgRoi')
        .addSelect('COUNT(CASE WHEN lead.roi_potential_score > 75 THEN 1 END)', 'highPotential')
        .groupBy('lead.processing_stage')
        .getRawMany();

      return stats.map(stat => ({
        stage: stat.stage,
        count: parseInt(stat.count),
        avgRoi: parseFloat(stat.avgRoi) || 0,
        highPotential: parseInt(stat.highPotential) || 0,
      }));
    } catch (error) {
      this.logger.error('Failed to get lead stats by stage', error.stack);
      throw new Error('Failed to retrieve lead statistics by stage');
    }
  }

  /**
   * Private helper methods
   */
  private async getTotalLeadsCount(): Promise<number> {
    return await this.leadRepository.count();
  }

  private async getTotalAgentsCount(): Promise<number> {
    return await this.agentRepository.count();
  }

  private async getActiveAgentsCount(): Promise<number> {
    return await this.agentRepository.count({ where: { status: AgentStatusEnum.ACTIVE } });
  }

  private async getCompletedLeadsCount(): Promise<number> {
    return await this.leadRepository.count({
      where: { processing_stage: ProcessingStage.REUNIAO_AGENDADA },
    });
  }

  private async getAverageProcessingTime(): Promise<number> {
    const result = await this.leadRepository
      .createQueryBuilder('lead')
      .select('AVG(EXTRACT(EPOCH FROM (lead.updated_at - lead.created_at)))', 'avgTime')
      .where('lead.processing_stage = :stage', { stage: 'reuniao_agendada' })
      .getRawOne();

    return parseFloat(result?.avgTime) || 0;
  }

  private async getAverageRoiPotential(): Promise<number> {
    const result = await this.leadRepository
      .createQueryBuilder('lead')
      .select('AVG(lead.roi_potential_score)', 'avgRoi')
      .getRawOne();

    return parseFloat(result?.avgRoi) || 0;
  }

  private async getDailyThroughput(startDate: Date, endDate: Date): Promise<number> {
    return await this.leadRepository.count({
      where: {
        processing_stage: ProcessingStage.REUNIAO_AGENDADA,
        updated_at: {
          gte: startDate,
          lte: endDate,
        } as any,
      },
    });
  }

  private async getDailyAverageProcessingTime(startDate: Date, endDate: Date): Promise<number> {
    const result = await this.leadRepository
      .createQueryBuilder('lead')
      .select('AVG(EXTRACT(EPOCH FROM (lead.updated_at - lead.created_at)))', 'avgTime')
      .where('lead.processing_stage = :stage', { stage: 'reuniao_agendada' })
      .andWhere('lead.updated_at BETWEEN :start AND :end', {
        start: startDate,
        end: endDate,
      })
      .getRawOne();

    return parseFloat(result?.avgTime) || 0;
  }

  private async getAgentSuccessCount(agentId: string): Promise<number> {
    // This would typically come from agent metrics or task completion logs
    // For now, return a placeholder calculation
    const agent = await this.agentRepository.findOne({ where: { id: agentId } });
    return agent?.metrics?.success_rate ? Math.floor(agent.metrics.success_rate * 10) : 0;
  }

  private async getAgentErrorCount(agentId: string): Promise<number> {
    // This would typically come from error logs or agent metrics
    // For now, return a placeholder calculation
    const agent = await this.agentRepository.findOne({ where: { id: agentId } });
    return agent?.metrics?.success_rate ? Math.floor((100 - agent.metrics.success_rate) * 0.1) : 0;
  }

  private async getAgentAverageProcessingTime(agentId: string): Promise<number> {
    const agent = await this.agentRepository.findOne({ where: { id: agentId } });
    return agent?.metrics?.processing_time_seconds || 0;
  }

  private async getAgentSuccessRate(agentId: string): Promise<number> {
    const agent = await this.agentRepository.findOne({ where: { id: agentId } });
    return agent?.metrics?.success_rate || 0;
  }

  private async getAgentQueueDepth(agentId: string): Promise<number> {
    const agent = await this.agentRepository.findOne({ where: { id: agentId } });
    return agent?.metrics?.queue_depth || 0;
  }

  private async getAgentThroughput(agentId: string): Promise<number> {
    const agent = await this.agentRepository.findOne({ where: { id: agentId } });
    return agent?.metrics?.throughput_per_hour || 0;
  }

  private async getAgentTokenUsage(agentId: string): Promise<number> {
    const agent = await this.agentRepository.findOne({ where: { id: agentId } });
    return agent?.metrics?.llm_usage?.total_tokens || 0;
  }

  private getPeriodDays(period: MetricsPeriod): number {
    switch (period) {
      case '24h':
        return 1;
      case '7d':
        return 7;
      case '30d':
        return 30;
      case '90d':
        return 90;
      default:
        return 7;
    }
  }
}
