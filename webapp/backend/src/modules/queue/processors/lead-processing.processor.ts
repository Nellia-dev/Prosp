import { Processor, Process } from '@nestjs/bull';
import { Logger, Injectable, Inject, forwardRef } from '@nestjs/common';
import { Job } from 'bull';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { ProcessingStage } from '@/shared/enums/nellia.enums';
import { Lead } from '@/database/entities/lead.entity';
import { Agent } from '@/database/entities/agent.entity';
import { AgentStatus } from '@/shared/enums/nellia.enums';
import { WebSocketService } from '../../websocket/websocket.service';
import { RealTimeEntity, RealTimeAction } from '../../websocket/dto/websocket.dto';

export interface LeadProcessingJobData {
  leadId: string;
  agentId: string;
  stage: string;
  retryCount?: number;
}

@Processor('lead-processing')
@Injectable()
export class LeadProcessingProcessor {
  private readonly logger = new Logger(LeadProcessingProcessor.name);

  constructor(
    @InjectRepository(Lead)
    private readonly leadRepository: Repository<Lead>,
    @InjectRepository(Agent)
    private readonly agentRepository: Repository<Agent>,
    @Inject(forwardRef(() => WebSocketService))
    private readonly webSocketService: WebSocketService,
  ) {}

  @Process('processLead')
  async handleLeadProcessing(job: Job<LeadProcessingJobData>) {
    const { leadId, agentId, stage } = job.data;
    
    this.logger.log(`Processing lead ${leadId} with agent ${agentId} for stage ${stage}`);

    try {
      // Update job progress
      await job.progress(10);

      // Get lead and agent
      const lead = await this.leadRepository.findOne({ where: { id: leadId } });
      const agent = await this.agentRepository.findOne({ where: { id: agentId } });

      if (!lead) {
        throw new Error(`Lead with ID ${leadId} not found`);
      }

      if (!agent) {
        throw new Error(`Agent with ID ${agentId} not found`);
      }

      // Update agent status to processing
      agent.status = AgentStatus.PROCESSING;
      agent.currentTask = `Processing lead: ${lead.company_name}`;
      await this.agentRepository.save(agent);

      // Broadcast agent status update
      this.webSocketService.broadcastAgentStatusUpdate({
        id: agent.id,
        name: agent.name,
        status: agent.status,
        current_task: agent.currentTask,
        last_updated: new Date().toISOString(),
      });

      await job.progress(25);

      // Simulate processing time based on stage complexity
      const processingTime = this.getProcessingTimeForStage(stage);
      await this.simulateProcessing(job, processingTime);

      await job.progress(75);

      // Update lead with processing results
      const previousStage = lead.processing_stage;
      lead.processing_stage = this.mapStageToEnum(stage);
      lead.updated_at = new Date();

      // Simulate some improvements to lead data
      if (stage === 'analyzing_refining') {
        lead.relevance_score = Math.min(lead.relevance_score + 0.1, 1.0);
      } else if (stage === 'possibly_qualified') {
        lead.roi_potential_score = Math.min(lead.roi_potential_score + 0.15, 1.0);
      }

      await this.leadRepository.save(lead);

      // Broadcast lead update
      this.webSocketService.broadcastLeadUpdate({
        id: lead.id,
        company_name: lead.company_name,
        website: lead.website,
        processing_stage: lead.processing_stage,
        qualification_tier: lead.qualification_tier,
        relevance_score: lead.relevance_score,
        roi_potential_score: lead.roi_potential_score,
        updated_at: lead.updated_at.toISOString(),
      });

      // Broadcast real-time update
      this.webSocketService.broadcastRealTimeUpdate({
        entity: RealTimeEntity.LEAD,
        action: RealTimeAction.UPDATE,
        data: {
          leadId: lead.id,
          previousStage,
          newStage: stage,
          agentId: agent.id,
        },
        timestamp: new Date().toISOString(),
      });

      await job.progress(90);

      // Update agent status back to active
      agent.status = AgentStatus.ACTIVE;
      agent.currentTask = null;
      agent.throughput = agent.throughput + 1;
      agent.llmTokenUsage = agent.llmTokenUsage + Math.floor(Math.random() * 1000) + 500;
      
      // Sync computed fields to metrics
      agent.syncFieldsToMetrics();
      await this.agentRepository.save(agent);

      // Final agent status update
      this.webSocketService.broadcastAgentStatusUpdate({
        id: agent.id,
        name: agent.name,
        status: agent.status,
        current_task: agent.currentTask,
        throughput: agent.throughput,
        llm_token_usage: agent.llmTokenUsage,
        last_updated: new Date().toISOString(),
      });

      await job.progress(100);

      this.logger.log(`Successfully processed lead ${leadId} with agent ${agentId}`);

      return {
        leadId,
        agentId,
        stage,
        previousStage,
        completedAt: new Date().toISOString(),
      };

    } catch (error) {
      this.logger.error(`Failed to process lead ${leadId}:`, error);

      // Update agent status to error
      const agent = await this.agentRepository.findOne({ where: { id: agentId } });
      if (agent) {
        agent.status = AgentStatus.ERROR;
        agent.currentTask = `Error processing lead: ${error.message}`;
        await this.agentRepository.save(agent);

        this.webSocketService.broadcastAgentStatusUpdate({
          id: agent.id,
          name: agent.name,
          status: agent.status,
          current_task: agent.currentTask,
          last_updated: new Date().toISOString(),
        });
      }
      throw error;
    }
  }

  @Process('batchProcessLeads')
  async handleBatchLeadProcessing(job: Job<{ leadIds: string[], agentId: string }>) {
    const { leadIds, agentId } = job.data;
    
    this.logger.log(`Batch processing ${leadIds.length} leads with agent ${agentId}`);

    const results = [];
    const totalLeads = leadIds.length;

    for (let i = 0; i < leadIds.length; i++) {
      const leadId = leadIds[i];
      const progress = Math.floor(((i + 1) / totalLeads) * 100);
      
      try {
        // Broadcast processing progress
        this.webSocketService.broadcastProcessingProgress({
          lead_id: leadId,
          current_agent: agentId,
          progress_percentage: progress,
          estimated_completion: new Date(Date.now() + (totalLeads - i) * 30000).toISOString(),
          current_step: `Processing lead ${i + 1} of ${totalLeads}`,
        });

        // Process individual lead (simplified for batch)
        const lead = await this.leadRepository.findOne({ where: { id: leadId } });
        if (lead) {
          lead.processing_stage = ProcessingStage.ANALYZING_REFINING;
          lead.updated_at = new Date();
          await this.leadRepository.save(lead);

          this.webSocketService.broadcastLeadUpdate({
            id: lead.id,
            company_name: lead.company_name,
            website: lead.website,
            processing_stage: lead.processing_stage,
            qualification_tier: lead.qualification_tier,
            relevance_score: lead.relevance_score,
            roi_potential_score: lead.roi_potential_score,
            updated_at: lead.updated_at.toISOString(),
          });

          results.push({ leadId, status: 'completed' });
        }

        await job.progress(progress);
        
        // Small delay between leads
        await new Promise(resolve => setTimeout(resolve, 1000));

      } catch (error) {
        this.logger.error(`Failed to process lead ${leadId} in batch:`, error);
        results.push({ leadId, status: 'failed', error: error.message });
      }
    }

    this.logger.log(`Batch processing completed. Processed ${results.length} leads`);
    return results;
  }

  private mapStageToEnum(stage: string): ProcessingStage {
    const stageMap: Record<string, ProcessingStage> = {
      'lead_qualification': ProcessingStage.LEAD_QUALIFICATION,
      'analyzing_refining': ProcessingStage.ANALYZING_REFINING,
      'possibly_qualified': ProcessingStage.POSSIBLY_QUALIFIED,
      'prospecting': ProcessingStage.PROSPECTING,
      'revisando': ProcessingStage.REVISANDO,
      'primeiras_mensagens': ProcessingStage.PRIMEIRAS_MENSAGENS,
      'negociando': ProcessingStage.NEGOCIANDO,
      'desqualificado': ProcessingStage.DESQUALIFICADO,
      'reuniao_agendada': ProcessingStage.REUNIAO_AGENDADA,
    };

    return stageMap[stage] || ProcessingStage.LEAD_QUALIFICATION;
  }

  private getProcessingTimeForStage(stage: string): number {
    const stageTimes = {
      'lead_qualification': 3000,
      'analyzing_refining': 5000,
      'possibly_qualified': 4000,
      'prospecting': 6000,
      'revisando': 3000,
      'primeiras_mensagens': 4000,
      'negociando': 7000,
      'reuniao_agendada': 2000,
    };

    return stageTimes[stage] || 4000;
  }

  private async simulateProcessing(job: Job, totalTime: number): Promise<void> {
    const steps = 10;
    const stepTime = totalTime / steps;

    for (let i = 0; i < steps; i++) {
      await new Promise(resolve => setTimeout(resolve, stepTime));
      const progress = 25 + Math.floor((i / steps) * 50); // Progress from 25% to 75%
      await job.progress(progress);
    }
  }
}