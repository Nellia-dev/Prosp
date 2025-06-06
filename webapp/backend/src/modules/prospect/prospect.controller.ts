import { Controller, Post, Get, Body, Param, Logger, HttpException, HttpStatus } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBody, ApiParam } from '@nestjs/swagger';
import { ProspectService, StartProspectingDto, ProspectJobStatus } from './prospect.service';
// QueueService is listed in the plan's constructor, but not directly used by controller methods.
// ProspectService encapsulates queue interactions. If QueueService is truly needed here,
// it would imply direct queue management from controller, which is less common.
// For now, omitting QueueService injection directly into controller as per typical patterns.

@ApiTags('prospect')
@Controller('prospect')
export class ProspectController {
  private readonly logger = new Logger(ProspectController.name);

  constructor(
    private prospectService: ProspectService,
    // private queueService: QueueService // As per plan, but ProspectService handles queue.
  ) {}

  @Post('start')
  @ApiOperation({ summary: 'Start a new prospecting process' })
  @ApiBody({ type: StartProspectingDto, description: 'Parameters for starting the prospecting process' })
  @ApiResponse({ status: 201, description: 'Prospecting process started successfully', type: Object }) // Adjust type if a specific Job DTO is returned
  @ApiResponse({ status: 400, description: 'Bad Request, e.g., business context not ready' })
  async startProspecting(@Body() dto: StartProspectingDto): Promise<{ jobId: string | number; status: string }> {
    this.logger.log(`Received request to start prospecting with query: ${dto.searchQuery}`);
    try {
      const job = await this.prospectService.startProspectingProcess(dto);
      this.logger.log(`Prospecting job created with ID: ${job.id}`);
      return { jobId: job.id, status: 'started' }; // Or await job.getState() for a more precise initial status
    } catch (error) {
      this.logger.error(`Failed to start prospecting process: ${error.message}`, error.stack);
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
  @ApiParam({ name: 'jobId', description: 'The ID of the prospecting job', type: String }) // Bull job IDs can be numbers or strings
  @ApiResponse({ status: 200, description: 'Job status retrieved successfully', type: Object }) // Define a ProspectJobStatus DTO for Swagger
  @ApiResponse({ status: 404, description: 'Job not found' })
  async getProspectStatus(@Param('jobId') jobId: string): Promise<ProspectJobStatus> {
    this.logger.log(`Received request for status of job ID: ${jobId}`);
    try {
      // Bull job IDs can be numbers, ensure service handles this or cast appropriately.
      // The service method getJobStatus already accepts string | number.
      return await this.prospectService.getJobStatus(jobId);
    } catch (error) {
      this.logger.error(`Failed to get status for job ${jobId}: ${error.message}`, error.stack);
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
  @ApiOperation({ summary: 'Get a list of recent prospecting jobs' })
  @ApiResponse({ status: 200, description: 'List of recent jobs retrieved successfully', type: [Object] }) // Define ProspectJobStatus DTO
  async getProspectJobs(): Promise<ProspectJobStatus[]> {
    this.logger.log('Received request to get recent prospect jobs');
    try {
      return await this.prospectService.getRecentJobs();
    } catch (error) {
      this.logger.error(`Failed to get recent jobs: ${error.message}`, error.stack);
      throw new HttpException(
        error.message || 'Failed to retrieve recent jobs',
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }
}
