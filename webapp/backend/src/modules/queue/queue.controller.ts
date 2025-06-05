import { Controller, Get, Post, Delete, Param, Body } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse } from '@nestjs/swagger';
import { QueueService } from './queue.service';
import { ProcessingStage } from '../../shared/types/nellia.types';

@ApiTags('Queue Management')
@Controller('queue')
export class QueueController {
  constructor(private readonly queueService: QueueService) {}

  @Get('stats')
  @ApiOperation({ summary: 'Get queue statistics' })
  @ApiResponse({ status: 200, description: 'Queue statistics retrieved successfully' })
  async getQueueStats() {
    return this.queueService.getQueueStats();
  }

  @Post('lead-processing')
  @ApiOperation({ summary: 'Add lead processing job' })
  @ApiResponse({ status: 201, description: 'Lead processing job added successfully' })
  async addLeadProcessingJob(@Body() body: { leadId: string; stage: ProcessingStage; priority?: number }) {
    const { leadId, stage, priority = 0 } = body;
    await this.queueService.addLeadProcessingJob(leadId, stage, priority);
    return { message: 'Lead processing job added successfully', leadId, stage };
  }

  @Post('bulk-lead-processing')
  @ApiOperation({ summary: 'Add bulk lead processing job' })
  @ApiResponse({ status: 201, description: 'Bulk lead processing job added successfully' })
  async addBulkLeadProcessingJob(@Body() body: { leadIds: string[]; priority?: number }) {
    const { leadIds, priority = 0 } = body;
    await this.queueService.addBulkLeadProcessingJob(leadIds, priority);
    return { message: 'Bulk lead processing job added successfully', leadCount: leadIds.length };
  }

  @Post('metrics-collection/agent')
  @ApiOperation({ summary: 'Schedule agent metrics collection' })
  @ApiResponse({ status: 201, description: 'Agent metrics collection scheduled successfully' })
  async scheduleAgentMetricsCollection(@Body() body: { agentId?: string }) {
    const { agentId } = body;
    await this.queueService.scheduleAgentMetricsCollection(agentId);
    return { message: 'Agent metrics collection scheduled successfully', agentId };
  }

  @Post('metrics-collection/system')
  @ApiOperation({ summary: 'Schedule system metrics collection' })
  @ApiResponse({ status: 201, description: 'System metrics collection scheduled successfully' })
  async scheduleSystemMetricsCollection() {
    await this.queueService.scheduleSystemMetricsCollection();
    return { message: 'System metrics collection scheduled successfully' };
  }

  @Post('cleanup/data')
  @ApiOperation({ summary: 'Schedule data cleanup' })
  @ApiResponse({ status: 201, description: 'Data cleanup scheduled successfully' })
  async scheduleDataCleanup() {
    await this.queueService.scheduleDataCleanup();
    return { message: 'Data cleanup scheduled successfully' };
  }

  @Post('cleanup/database')
  @ApiOperation({ summary: 'Schedule database maintenance' })
  @ApiResponse({ status: 201, description: 'Database maintenance scheduled successfully' })
  async scheduleDatabaseMaintenance() {
    await this.queueService.scheduleDatabaseMaintenance();
    return { message: 'Database maintenance scheduled successfully' };
  }

  @Post(':queueName/pause')
  @ApiOperation({ summary: 'Pause a queue' })
  @ApiResponse({ status: 200, description: 'Queue paused successfully' })
  async pauseQueue(@Param('queueName') queueName: string) {
    await this.queueService.pauseQueue(queueName);
    return { message: `Queue ${queueName} paused successfully` };
  }

  @Post(':queueName/resume')
  @ApiOperation({ summary: 'Resume a queue' })
  @ApiResponse({ status: 200, description: 'Queue resumed successfully' })
  async resumeQueue(@Param('queueName') queueName: string) {
    await this.queueService.resumeQueue(queueName);
    return { message: `Queue ${queueName} resumed successfully` };
  }

  @Delete(':queueName/clear')
  @ApiOperation({ summary: 'Clear a queue' })
  @ApiResponse({ status: 200, description: 'Queue cleared successfully' })
  async clearQueue(@Param('queueName') queueName: string) {
    await this.queueService.clearQueue(queueName);
    return { message: `Queue ${queueName} cleared successfully` };
  }

  @Post('initialize')
  @ApiOperation({ summary: 'Initialize all scheduled jobs' })
  @ApiResponse({ status: 200, description: 'Scheduled jobs initialized successfully' })
  async initializeScheduledJobs() {
    await this.queueService.initializeScheduledJobs();
    return { message: 'All scheduled jobs initialized successfully' };
  }
}