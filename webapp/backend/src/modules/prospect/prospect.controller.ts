import { Controller, Post, Get, Body, Param, Logger, HttpException, HttpStatus, Req, UseGuards } from '@nestjs/common';
import { Request } from 'express';
import { ApiTags, ApiOperation, ApiResponse, ApiBody, ApiParam } from '@nestjs/swagger';
import { ProspectService, StartProspectingDto, ProspectJobStatus } from './prospect.service';
import { UserId } from '../auth/user-id.decorator';
import { ApiBearerAuth } from '@nestjs/swagger';
import { AuthGuard } from '@nestjs/passport';

interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
  };
}
@ApiBearerAuth()
@UseGuards(AuthGuard('jwt'))
@ApiTags('prospect')
@Controller('prospect')
export class ProspectController {
  private readonly logger = new Logger(ProspectController.name);

  constructor(
    private prospectService: ProspectService,
  ) {}

  @Post('start')
  @ApiOperation({ summary: 'Start a new prospecting process based on the user\'s business context.' })
  @ApiResponse({ status: 201, description: 'Prospecting process started successfully', type: Object })
  @ApiResponse({ status: 400, description: 'Bad Request, e.g., business context not ready' })
  @ApiResponse({ status:403, description: 'Quota exceeded or insufficient permissions' })
  @ApiResponse({ status: 409, description: 'Another prospecting job is already running for this user' })
  async startProspecting(
    @UserId() userId: string
  ): Promise<{ jobId: string | number; status: string }> {
    if (!userId) {
      throw new HttpException('User not authenticated', HttpStatus.UNAUTHORIZED);
    }
    this.logger.log(`User ${userId} received request to start prospecting.`);
    
    try {
      const job = await this.prospectService.startProspectingProcess(userId);
      this.logger.log(`Prospecting job created for user ${userId} with ID: ${job.id}`);
      return { jobId: job.id, status: 'started' };
    } catch (error) {
      this.logger.error(`Failed to start prospecting process for user ${userId}: ${error.message}`, error.stack);
      if (error instanceof HttpException) {
        throw error;
      }
      throw new HttpException(
        error.message || 'Failed to start prospecting process', 
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }

  @Get('status/:jobId')
  @ApiOperation({ summary: 'Get the status of a specific prospecting job' })
  @ApiParam({ name: 'jobId', description: 'The ID of the prospecting job', type: String })
  @ApiResponse({ status: 200, description: 'Job status retrieved successfully', type: Object })
  @ApiResponse({ status: 403, description: 'Access denied - job does not belong to user' })
  @ApiResponse({ status: 404, description: 'Job not found' })
  async getProspectStatus(
    @Param('jobId') jobId: string,
    @UserId() userId: string
  ): Promise<ProspectJobStatus> {
    if (!userId) {
      throw new HttpException('User not authenticated', HttpStatus.UNAUTHORIZED);
    }
    if (!jobId) {
      throw new HttpException('Job ID is required', HttpStatus.BAD_REQUEST);
    }

    this.logger.log(`User ${userId} received request for status of job ID: ${jobId}`);
    
    try {
      return await this.prospectService.getJobStatus(jobId, userId);
    } catch (error) {
      this.logger.error(`Failed to get status for job ${jobId} for user ${userId}: ${error.message}`, error.stack);
      if (error instanceof HttpException) {
        throw error;
      }
      throw new HttpException(
        error.message || `Failed to get status for job ${jobId}`,
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }

  @Get('jobs')
  @ApiOperation({ summary: 'Get a list of recent prospecting jobs for the current user' })
  @ApiResponse({ status: 200, description: 'List of recent jobs retrieved successfully', type: [Object] })
  async getProspectJobs(@UserId() userId: string): Promise<ProspectJobStatus[]> {
    if (!userId) {
      throw new HttpException('User not authenticated', HttpStatus.UNAUTHORIZED);
    }
    
    this.logger.log(`User ${userId} received request to get recent prospect jobs`);
    
    try {
      return await this.prospectService.getRecentJobs(userId);
    } catch (error) {
      this.logger.error(`Failed to get recent jobs for user ${userId}: ${error.message}`, error.stack);
      throw new HttpException(
        error.message || 'Failed to retrieve recent jobs',
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }
}
