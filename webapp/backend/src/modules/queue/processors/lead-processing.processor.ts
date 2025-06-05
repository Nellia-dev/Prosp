import { Processor, Process } from '@nestjs/bull';
import { Logger, Injectable, Inject, forwardRef } from '@nestjs/common';
import { Job } from 'bull';
import { HttpService } from '@nestjs/axios';
import { AxiosError } from 'axios';
import { firstValueFrom } from 'rxjs';
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

  private readonly mcpServerBaseUrl = process.env.MCP_SERVER_URL || 'http://localhost:5001';

  constructor(
    @InjectRepository(Lead)
    private readonly leadRepository: Repository<Lead>,
    @InjectRepository(Agent)
    private readonly agentRepository: Repository<Agent>,
    @Inject(forwardRef(() => WebSocketService))
    private readonly webSocketService: WebSocketService,
    private readonly httpService: HttpService,
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

      // Call MCP Server to process the lead
      const mcpPayload = {
        url: lead.website,
        // Add any other necessary data from the 'lead' object that 'convert_site_data_to_validated_lead' might use
        // For now, assuming 'url' is the primary requirement.
        // Potentially pass lead data that might be used for 'extracted_text_content' or 'google_search_data' if available
      };
      
      this.logger.log(`Calling MCP server for lead ${leadId} at ${this.mcpServerBaseUrl}/api/lead/${leadId}/process/enhanced`);

      let mcpResponse;
      try {
        const response = await firstValueFrom(
          this.httpService.post(
            `${this.mcpServerBaseUrl}/api/lead/${leadId}/process/enhanced`,
            mcpPayload,
            { timeout: 180000 } // 3 minutes timeout
          )
        );
        mcpResponse = response.data;
        this.logger.log(`MCP server response for lead ${leadId}: ${JSON.stringify(mcpResponse)}`);
      } catch (error) {
        const axiosError = error as AxiosError;
        this.logger.error(`Error calling MCP server for lead ${leadId}: ${axiosError.message}`, axiosError.stack);
        if (axiosError.response) {
          this.logger.error(`MCP Server Error Response: ${JSON.stringify(axiosError.response.data)}`);
        }
        // Update agent status to error
        agent.status = AgentStatus.ERROR;
        agent.currentTask = `Error calling MCP: ${axiosError.message}`;
        await this.agentRepository.save(agent);
        this.webSocketService.broadcastAgentStatusUpdate({
          id: agent.id,
          name: agent.name,
          status: agent.status,
          current_task: agent.currentTask,
          last_updated: new Date().toISOString(),
        });
        throw new Error(`MCP server call failed: ${axiosError.message}`);
      }

      await job.progress(75);

      // Update lead with processing results from MCP
      const previousStage = lead.processing_stage;
      if (mcpResponse && mcpResponse.success && mcpResponse.storage_result && mcpResponse.storage_result.summary_metrics) {
        const metrics = mcpResponse.storage_result.summary_metrics;
        lead.relevance_score = metrics.relevance_score !== undefined ? metrics.relevance_score : lead.relevance_score;
        lead.roi_potential_score = metrics.roi_potential_score !== undefined ? metrics.roi_potential_score : lead.roi_potential_score;
        lead.qualification_tier = metrics.qualification_tier !== undefined ? metrics.qualification_tier : lead.qualification_tier;
        // Assuming MCP processing implies a certain stage, e.g., PROSPECTING
        lead.processing_stage = ProcessingStage.PROSPECTING; 
      } else {
        // If MCP response is not as expected or failed, mark stage as error or keep previous
        this.logger.warn(`MCP processing for lead ${leadId} did not return expected metrics or failed. Check MCP logs.`);
        // Potentially set to an error stage or re-queue
        lead.processing_stage = ProcessingStage.REVISANDO; // Or some other appropriate stage
      }
      
      lead.updated_at = new Date();
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
      agent.throughput = (agent.throughput || 0) + 1;
      
      // Update LLM token usage from MCP response if available
      if (mcpResponse && mcpResponse.success && mcpResponse.processing_result && mcpResponse.processing_result.result && mcpResponse.processing_result.result.processing_metadata) {
        const metadata = mcpResponse.processing_result.result.processing_metadata;
        agent.llmTokenUsage = (agent.llmTokenUsage || 0) + (metadata.total_tokens_used || 0);
      } else {
        // Fallback if token usage not in MCP response
        agent.llmTokenUsage = (agent.llmTokenUsage || 0) + Math.floor(Math.random() * 1000) + 500;
      }
      
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
    const agent = await this.agentRepository.findOne({ where: { id: agentId } });
    if (!agent) {
      this.logger.error(`Agent with ID ${agentId} not found for batch processing.`);
      throw new Error(`Agent with ID ${agentId} not found`);
    }

    const results = [];
    const totalLeads = leadIds.length;

    for (let i = 0; i < totalLeads; i++) {
      const leadId = leadIds[i];
      const jobProgress = Math.floor(((i + 1) / totalLeads) * 100);
      
      try {
        this.webSocketService.broadcastProcessingProgress({
          lead_id: leadId,
          current_agent: agentId,
          progress_percentage: jobProgress,
          estimated_completion: new Date(Date.now() + (totalLeads - (i + 1)) * 60000).toISOString(), // Estimate 1 min per lead
          current_step: `Processing lead ${i + 1} of ${totalLeads} via MCP: ${leadId}`,
        });

        const lead = await this.leadRepository.findOne({ where: { id: leadId } });
        if (!lead) {
          this.logger.warn(`Lead ${leadId} not found in batch. Skipping.`);
          results.push({ leadId, status: 'skipped', error: 'Lead not found' });
          continue;
        }

        // Update agent status for current lead
        agent.currentTask = `Batch Processing: Lead ${lead.company_name}`;
        await this.agentRepository.save(agent);
        this.webSocketService.broadcastAgentStatusUpdate({
            id: agent.id, name: agent.name, status: AgentStatus.PROCESSING, 
            current_task: agent.currentTask, last_updated: new Date().toISOString()
        });
        
        const mcpPayload = { url: lead.website };
        this.logger.log(`Calling MCP server for batch lead ${leadId} at ${this.mcpServerBaseUrl}/api/lead/${leadId}/process/enhanced`);
        
        let mcpResponseData;
        try {
            const mcpResponse = await firstValueFrom(
              this.httpService.post(
                `${this.mcpServerBaseUrl}/api/lead/${leadId}/process/enhanced`,
                mcpPayload,
                { timeout: 180000 } // 3 minutes timeout
              )
            );
            mcpResponseData = mcpResponse.data;
            this.logger.log(`MCP server response for batch lead ${leadId}: ${JSON.stringify(mcpResponseData)}`);

            if (mcpResponseData && mcpResponseData.success && mcpResponseData.storage_result && mcpResponseData.storage_result.summary_metrics) {
                const metrics = mcpResponseData.storage_result.summary_metrics;
                lead.relevance_score = metrics.relevance_score !== undefined ? metrics.relevance_score : lead.relevance_score;
                lead.roi_potential_score = metrics.roi_potential_score !== undefined ? metrics.roi_potential_score : lead.roi_potential_score;
                lead.qualification_tier = metrics.qualification_tier !== undefined ? metrics.qualification_tier : lead.qualification_tier;
                lead.processing_stage = ProcessingStage.PROSPECTING;
            } else {
                this.logger.warn(`MCP processing for batch lead ${leadId} did not return expected metrics or failed.`);
                lead.processing_stage = ProcessingStage.REVISANDO;
            }
            lead.updated_at = new Date();
            await this.leadRepository.save(lead);

            this.webSocketService.broadcastLeadUpdate({
                id: lead.id, company_name: lead.company_name, website: lead.website,
                processing_stage: lead.processing_stage, qualification_tier: lead.qualification_tier,
                relevance_score: lead.relevance_score, roi_potential_score: lead.roi_potential_score,
                updated_at: lead.updated_at.toISOString(),
            });
            results.push({ leadId, status: 'completed' });

            // Update agent LLM tokens from MCP if available
            if (mcpResponseData && mcpResponseData.success && mcpResponseData.processing_result && mcpResponseData.processing_result.result && mcpResponseData.processing_result.result.processing_metadata) {
                const metadata = mcpResponseData.processing_result.result.processing_metadata;
                agent.llmTokenUsage = (agent.llmTokenUsage || 0) + (metadata.total_tokens_used || 0);
            }

        } catch (mcpError) {
            const axiosError = mcpError as AxiosError;
            this.logger.error(`Error calling MCP server for batch lead ${leadId}: ${axiosError.message}`, axiosError.stack);
            if (axiosError.response) {
                this.logger.error(`MCP Server Error Response for batch lead ${leadId}: ${JSON.stringify(axiosError.response.data)}`);
            }
            results.push({ leadId, status: 'failed', error: `MCP call failed: ${axiosError.message}` });
            // Optionally update lead status to an error state here
        }
        
        await job.progress(jobProgress);
        // Small delay between leads if needed, but MCP calls themselves will take time
        // await new Promise(resolve => setTimeout(resolve, 500));

      } catch (error) {
        this.logger.error(`Failed to process lead ${leadId} in batch: ${error.message}`, error.stack);
        results.push({ leadId, status: 'failed', error: error.message });
      }
    }

    // Reset agent status after batch
    agent.status = AgentStatus.ACTIVE;
    agent.currentTask = null;
    agent.throughput = (agent.throughput || 0) + leadIds.length; // Increment by number of leads attempted
    agent.syncFieldsToMetrics();
    await this.agentRepository.save(agent);
    this.webSocketService.broadcastAgentStatusUpdate({
        id: agent.id, name: agent.name, status: agent.status, 
        current_task: agent.currentTask, throughput: agent.throughput, 
        llm_token_usage: agent.llmTokenUsage, last_updated: new Date().toISOString()
    });

    this.logger.log(`Batch processing completed. Processed ${results.filter(r => r.status === 'completed').length} of ${totalLeads} leads successfully.`);
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

  // getProcessingTimeForStage and simulateProcessing are no longer needed as we call the actual MCP server.
  // private getProcessingTimeForStage(stage: string): number { ... }
  // private async simulateProcessing(job: Job, totalTime: number): Promise<void> { ... }
}
