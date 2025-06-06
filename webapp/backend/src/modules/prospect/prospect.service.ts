import { Injectable, BadRequestException, NotFoundException, Logger } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bull';
import { Queue, Job } from 'bull';
import { BusinessContextService } from '../business-context/business-context.service';
import { McpService } from '../mcp/mcp.service';
// Assuming these DTOs/types will be defined, possibly in shared/types or a local dtos file
// For now, defining inline for clarity based on the plan.
import { ApiProperty } from '@nestjs/swagger'; // Import for DTO class

export class StartProspectingDto {
  @ApiProperty({ example: 'tech companies in Brazil', description: 'The search query for prospecting' })
  searchQuery: string;

  @ApiProperty({ example: 20, description: 'Maximum number of sites to process', required: false, default: 10 })
  maxSites?: number;
}

export interface HarvesterJobData {
  searchQuery: string;
  maxSites: number;
  contextId: string | null; // Assuming contextId might be relevant
  timestamp: string;
}

export interface ProspectJobStatus {
  id: string | number; // Job ID can be string or number depending on Bull version/config
  status: string; // e.g., 'waiting', 'active', 'completed', 'failed', 'delayed'
  progress: number | object; // Progress can be a number (0-100) or an object
  data: HarvesterJobData;
  result: any;
  error: string | null;
  createdAt: Date;
  processedAt: Date | null;
  finishedAt: Date | null;
}

@Injectable()
export class ProspectService {
  private readonly logger = new Logger(ProspectService.name);

  constructor(
    @InjectQueue('prospect-processing') private prospectQueue: Queue<HarvesterJobData>,
    private businessContextService: BusinessContextService,
    private mcpService: McpService, // Assuming McpService is available and configured
  ) {}

  async startProspectingProcess(dto: StartProspectingDto): Promise<Job<HarvesterJobData>> {
    this.logger.log(`Attempting to start prospecting process with query: ${dto.searchQuery}`);

    const contextReadiness = await this.businessContextService.isReadyForProspecting();
    if (!contextReadiness.ready) {
      this.logger.warn(`Business context not ready. Missing fields: ${contextReadiness.missingFields.join(', ')}`);
      throw new BadRequestException(
        `Business context not ready for prospecting. Missing: ${contextReadiness.missingFields.join(', ')}`
      );
    }
    
    // Assuming 'default' or a specific ID if context exists and is relevant for the job.
    // The plan uses `contextId: contextReady.contextExists ? 'default' : null`
    // This implies the harvester job might need the context ID.
    // For now, let's assume the business context itself is fetched within the processor if needed.
    const context = await this.businessContextService.getContextForMcp();
    if (!context && contextReadiness.contextExists) {
        this.logger.error('Context exists but could not be fetched for MCP.');
        throw new Error('Failed to fetch existing business context for prospecting job.');
    }


    const jobData: HarvesterJobData = {
      searchQuery: dto.searchQuery,
      maxSites: dto.maxSites || 10, // Default to 10 as per plan
      contextId: context ? context.id : null, // Pass context ID if available
      timestamp: new Date().toISOString(),
    };

    const job = await this.prospectQueue.add('run-harvester', jobData, {
      attempts: 3,
      backoff: {
        type: 'exponential',
        delay: 2000,
      },
      removeOnComplete: true, // Optional: clean up completed jobs
      removeOnFail: 50, // Optional: keep some failed jobs for inspection
    });

    this.logger.log(`Prospecting job added to queue. Job ID: ${job.id}`);
    return job;
  }

  async getJobStatus(jobId: string | number): Promise<ProspectJobStatus> {
    this.logger.log(`Fetching status for job ID: ${jobId}`);
    const job = await this.prospectQueue.getJob(jobId);

    if (!job) {
      this.logger.warn(`Job with ID ${jobId} not found.`);
      throw new NotFoundException(`Job with ID ${jobId} not found`);
    }

    const status = await job.getState();
    this.logger.log(`Job ${jobId} status: ${status}`);

    return {
      id: job.id,
      status: status,
      progress: job.progress(),
      data: job.data,
      result: job.returnvalue,
      error: job.failedReason,
      createdAt: new Date(job.timestamp),
      processedAt: job.processedOn ? new Date(job.processedOn) : null,
      finishedAt: job.finishedOn ? new Date(job.finishedOn) : null,
    };
  }

  async getRecentJobs(count = 10): Promise<ProspectJobStatus[]> {
    this.logger.log(`Fetching ${count} recent jobs.`);
    // Bull typically returns jobs in specific states.
    // To get "recent" jobs, we might fetch completed, failed, active, waiting.
    const jobTypes: ('waiting' | 'active' | 'completed' | 'failed' | 'delayed')[] = 
      ['completed', 'failed', 'active', 'waiting', 'delayed'];
    
    let recentJobs: Job<HarvesterJobData>[] = [];
    for (const type of jobTypes) {
      const jobs = await this.prospectQueue.getJobs([type], 0, count - 1, true); // true for ascending order (oldest first)
      recentJobs.push(...jobs);
    }

    // Sort by timestamp descending to get the most recent ones across all types
    recentJobs.sort((a, b) => b.timestamp - a.timestamp);
    
    // Slice to the desired count
    const limitedJobs = recentJobs.slice(0, count);

    const jobStatuses = await Promise.all(
      limitedJobs.map(async (job) => ({
        id: job.id,
        status: await job.getState(),
        progress: job.progress(),
        data: job.data,
        result: job.returnvalue,
        error: job.failedReason,
        createdAt: new Date(job.timestamp),
        processedAt: job.processedOn ? new Date(job.processedOn) : null,
        finishedAt: job.finishedOn ? new Date(job.finishedOn) : null,
      })),
    );
    this.logger.log(`Found ${jobStatuses.length} recent jobs.`);
    return jobStatuses;
  }
}
