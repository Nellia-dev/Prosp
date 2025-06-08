import { Injectable, BadRequestException, NotFoundException, ConflictException, ForbiddenException, Logger } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bull';
import { Queue, Job } from 'bull';
import { BusinessContextService } from '../business-context/business-context.service';
import { McpService } from '../mcp/mcp.service';
import { UsersService } from '../users/users.service';
import { QuotaService } from '../quota/quota.service';
import { ApiProperty } from '@nestjs/swagger';
import { BusinessContext as BusinessContextType } from '@/shared/types/nellia.types';

export class StartProspectingDto {
  // This DTO is now empty as the backend will derive the necessary parameters.
}

export interface HarvesterJobData {
  userId: string; // ID of the user who initiated the job
  searchQuery: string;
  maxSites: number;
  maxLeadsToReturn: number; // Calculated based on user's remaining quota
  businessContext: BusinessContextType; // Pass the full context
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
    private mcpService: McpService,
    private usersService: UsersService,
    private quotaService: QuotaService,
  ) {}

  /**
   * Start prospecting process for a specific user with quota and job checks
   */
  async startProspectingProcess(userId: string): Promise<Job<HarvesterJobData>> {
    this.logger.log(`User ${userId} attempting to start prospecting process.`);

    // Step 1: Validate Business Context
    const contextReadiness = await this.businessContextService.isReadyForProspecting(userId);
    if (!contextReadiness.ready) {
      this.logger.warn(`Business context not ready for user ${userId}. Missing fields: ${contextReadiness.missingFields.join(', ')}`);
      throw new BadRequestException(
        `Business context not ready for prospecting. Missing: ${contextReadiness.missingFields.join(', ')}`
      );
    }

    // Step 2: Check User Quota & Concurrent Jobs
    const user = await this.usersService.getUserById(userId);
    if (user.prospectingJobId) {
      // Check if a job is already running for this user
      const existingJob = await this.prospectQueue.getJob(user.prospectingJobId);
      if (existingJob && ['active', 'waiting', 'delayed'].includes(await existingJob.getState())) {
        throw new ConflictException('A prospecting job is already running for your account.');
      } else {
        // Clear stale job ID
        await this.usersService.clearProspectingJob(userId);
      }
    }

    const maxLeadsUserCanRequest = await this.quotaService.getMaxLeadsToRequest(userId);
    if (maxLeadsUserCanRequest <= 0) {
      throw new ForbiddenException('Lead generation quota exceeded or no quota remaining for this request.');
    }

    // Step 3: Get Business Context
    const context = await this.businessContextService.getContextForMcp(userId);
    if (!context) {
      this.logger.error(`Context for user ${userId} could not be fetched for MCP.`);
      throw new Error('Failed to fetch business context for prospecting job.');
    }

    // Step 4: Prepare Job Data
    const jobData: HarvesterJobData = {
      userId: userId,
      searchQuery: context.business_description, // Use business description as the query
      maxSites: 10, // Hardcoded default, as per user request
      maxLeadsToReturn: maxLeadsUserCanRequest, // Key: limit for MCP
      businessContext: context,
      timestamp: new Date().toISOString(),
    };

    // Step 5: Add Job to Queue & Record Job ID on User
    const job = await this.prospectQueue.add('run-harvester', jobData, {
      attempts: 3,
      backoff: {
        type: 'exponential',
        delay: 2000,
      },
      removeOnComplete: true, // Optional: clean up completed jobs
      removeOnFail: 50, // Optional: keep some failed jobs for inspection
    });

    await this.usersService.recordProspectingJobStart(userId, job.id.toString());

    this.logger.log(`Prospecting job added to queue for user ${userId}. Job ID: ${job.id}`);
    return job;
  }

  /**
   * Get job status, ensuring job belongs to the user
   */
  async getJobStatus(jobId: string | number, userId: string): Promise<ProspectJobStatus> {
    this.logger.log(`User ${userId} fetching status for job ID: ${jobId}`);
    const job = await this.prospectQueue.getJob(jobId);

    if (!job) {
      this.logger.warn(`Job with ID ${jobId} not found.`);
      throw new NotFoundException(`Job with ID ${jobId} not found`);
    }

    // Ensure job belongs to the user
    if (job.data.userId !== userId) {
      throw new ForbiddenException('You do not have permission to access this job');
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

  /**
   * Get recent jobs for a specific user
   */
  async getRecentJobs(userId: string, count = 10): Promise<ProspectJobStatus[]> {
    this.logger.log(`Fetching ${count} recent jobs for user ${userId}.`);
    
    const jobTypes: ('waiting' | 'active' | 'completed' | 'failed' | 'delayed')[] = 
      ['completed', 'failed', 'active', 'waiting', 'delayed'];
    
    let recentJobs: Job<HarvesterJobData>[] = [];
    for (const type of jobTypes) {
      const jobs = await this.prospectQueue.getJobs([type], 0, 50, true); // Get more to filter by user
      // Filter jobs by userId
      const userJobs = jobs.filter(job => job.data.userId === userId);
      recentJobs.push(...userJobs);
    }

    // Sort by timestamp descending to get the most recent ones
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
    
    this.logger.log(`Found ${jobStatuses.length} recent jobs for user ${userId}.`);
    return jobStatuses;
  }
}
