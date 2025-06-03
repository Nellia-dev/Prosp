import {
  Controller,
  Get,
  Query,
  Param,
  HttpStatus,
  HttpException,
  Logger,
} from '@nestjs/common';
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiQuery,
  ApiParam,
} from '@nestjs/swagger';
import { MetricsService } from './metrics.service';
import {
  DashboardMetrics,
  AgentPerformanceData,
  PerformanceDataPoint,
  MetricsPeriod,
  AgentMetrics,
} from '../../shared/types/nellia.types';

@ApiTags('metrics')
@Controller('metrics')
export class MetricsController {
  private readonly logger = new Logger(MetricsController.name);

  constructor(private readonly metricsService: MetricsService) {}

  @Get('dashboard')
  @ApiOperation({ summary: 'Get comprehensive dashboard metrics' })
  @ApiResponse({
    status: 200,
    description: 'Dashboard metrics retrieved successfully',
  })
  @ApiResponse({
    status: 500,
    description: 'Internal server error',
  })
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    try {
      this.logger.log('Fetching dashboard metrics');
      const metrics = await this.metricsService.getDashboardMetrics();
      this.logger.log('Dashboard metrics retrieved successfully');
      return metrics;
    } catch (error) {
      this.logger.error('Failed to get dashboard metrics', error.stack);
      throw new HttpException(
        'Failed to retrieve dashboard metrics',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get('performance')
  @ApiOperation({ summary: 'Get performance data over time for charts' })
  @ApiQuery({
    name: 'period',
    required: false,
    enum: ['24h', '7d', '30d', '90d'],
    description: 'Time period for performance data',
  })
  @ApiResponse({
    status: 200,
    description: 'Performance data retrieved successfully',
  })
  @ApiResponse({
    status: 400,
    description: 'Invalid period parameter',
  })
  @ApiResponse({
    status: 500,
    description: 'Internal server error',
  })
  async getPerformanceData(
    @Query('period') period: MetricsPeriod = '7d',
  ): Promise<PerformanceDataPoint[]> {
    try {
      this.logger.log(`Fetching performance data for period: ${period}`);
      
      // Validate period
      const validPeriods: MetricsPeriod[] = ['24h', '7d', '30d', '90d'];
      if (period && !validPeriods.includes(period)) {
        throw new HttpException(
          'Invalid period. Must be one of: 24h, 7d, 30d, 90d',
          HttpStatus.BAD_REQUEST,
        );
      }

      const performanceData = await this.metricsService.getPerformanceData(period);
      this.logger.log(`Performance data retrieved for ${performanceData.length} data points`);
      return performanceData;
    } catch (error) {
      if (error instanceof HttpException) {
        throw error;
      }
      this.logger.error('Failed to get performance data', error.stack);
      throw new HttpException(
        'Failed to retrieve performance data',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get('agents/performance')
  @ApiOperation({ summary: 'Get agent performance data for comparison charts' })
  @ApiResponse({
    status: 200,
    description: 'Agent performance data retrieved successfully',
  })
  @ApiResponse({
    status: 500,
    description: 'Internal server error',
  })
  async getAgentPerformanceData(): Promise<AgentPerformanceData[]> {
    try {
      this.logger.log('Fetching agent performance data');
      const performanceData = await this.metricsService.getAgentPerformanceData();
      this.logger.log(`Agent performance data retrieved for ${performanceData.length} agents`);
      return performanceData;
    } catch (error) {
      this.logger.error('Failed to get agent performance data', error.stack);
      throw new HttpException(
        'Failed to retrieve agent performance data',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get('agents/:agentId')
  @ApiOperation({ summary: 'Get metrics for a specific agent' })
  @ApiParam({
    name: 'agentId',
    description: 'Agent ID',
    example: 'uuid-string',
  })
  @ApiResponse({
    status: 200,
    description: 'Agent metrics retrieved successfully',
  })
  @ApiResponse({
    status: 404,
    description: 'Agent not found',
  })
  @ApiResponse({
    status: 500,
    description: 'Internal server error',
  })
  async getAgentMetrics(@Param('agentId') agentId: string): Promise<AgentMetrics[]> {
    try {
      this.logger.log(`Fetching metrics for agent: ${agentId}`);
      const metrics = await this.metricsService.getAgentMetrics(agentId);
      
      if (metrics.length === 0) {
        throw new HttpException(
          `Agent with ID ${agentId} not found`,
          HttpStatus.NOT_FOUND,
        );
      }

      this.logger.log(`Metrics retrieved for agent: ${agentId}`);
      return metrics;
    } catch (error) {
      if (error instanceof HttpException) {
        throw error;
      }
      this.logger.error(`Failed to get metrics for agent ${agentId}`, error.stack);
      throw new HttpException(
        'Failed to retrieve agent metrics',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get('agents')
  @ApiOperation({ summary: 'Get metrics for all agents' })
  @ApiResponse({
    status: 200,
    description: 'All agent metrics retrieved successfully',
  })
  @ApiResponse({
    status: 500,
    description: 'Internal server error',
  })
  async getAllAgentMetrics(): Promise<AgentMetrics[]> {
    try {
      this.logger.log('Fetching metrics for all agents');
      const metrics = await this.metricsService.getAgentMetrics();
      this.logger.log(`Metrics retrieved for ${metrics.length} agents`);
      return metrics;
    } catch (error) {
      this.logger.error('Failed to get all agent metrics', error.stack);
      throw new HttpException(
        'Failed to retrieve agent metrics',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get('leads/stats-by-stage')
  @ApiOperation({ summary: 'Get lead statistics grouped by processing stage' })
  @ApiResponse({
    status: 200,
    description: 'Lead statistics by stage retrieved successfully',
  })
  @ApiResponse({
    status: 500,
    description: 'Internal server error',
  })
  async getLeadStatsByStage() {
    try {
      this.logger.log('Fetching lead statistics by stage');
      const stats = await this.metricsService.getLeadStatsByStage();
      this.logger.log(`Lead statistics retrieved for ${stats.length} stages`);
      return stats;
    } catch (error) {
      this.logger.error('Failed to get lead stats by stage', error.stack);
      throw new HttpException(
        'Failed to retrieve lead statistics by stage',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Get('summary')
  @ApiOperation({ summary: 'Get summary metrics for quick overview' })
  @ApiResponse({
    status: 200,
    description: 'Summary metrics retrieved successfully',
  })
  @ApiResponse({
    status: 500,
    description: 'Internal server error',
  })
  async getSummaryMetrics() {
    try {
      this.logger.log('Fetching summary metrics');
      
      const [dashboardMetrics, leadStats, agentPerformance] = await Promise.all([
        this.metricsService.getDashboardMetrics(),
        this.metricsService.getLeadStatsByStage(),
        this.metricsService.getAgentPerformanceData(),
      ]);

      const summary = {
        overview: {
          totalLeads: dashboardMetrics.totalLeads,
          completedLeads: dashboardMetrics.completedLeads,
          successRate: dashboardMetrics.successRate,
          averageRoiPotential: dashboardMetrics.averageRoiPotential,
        },
        stageDistribution: leadStats,
        agentSummary: {
          totalAgents: agentPerformance.length,
          performance: agentPerformance.length > 0 ? {
            totalSuccess: agentPerformance.reduce((sum, agent) => sum + agent.success, 0),
            totalErrors: agentPerformance.reduce((sum, agent) => sum + agent.errors, 0),
            totalProcessingTime: agentPerformance.reduce((sum, agent) => sum + agent.avgProcessingTime, 0),
            avgSuccess: agentPerformance.reduce((sum, agent) => sum + agent.success, 0) / agentPerformance.length,
            avgErrors: agentPerformance.reduce((sum, agent) => sum + agent.errors, 0) / agentPerformance.length,
            avgProcessingTime: agentPerformance.reduce((sum, agent) => sum + agent.avgProcessingTime, 0) / agentPerformance.length,
          } : {
            totalSuccess: 0,
            totalErrors: 0,
            totalProcessingTime: 0,
            avgSuccess: 0,
            avgErrors: 0,
            avgProcessingTime: 0,
          },
        },
        lastUpdated: dashboardMetrics.lastUpdated,
      };

      this.logger.log('Summary metrics retrieved successfully');
      return summary;
    } catch (error) {
      this.logger.error('Failed to get summary metrics', error.stack);
      throw new HttpException(
        'Failed to retrieve summary metrics',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}
