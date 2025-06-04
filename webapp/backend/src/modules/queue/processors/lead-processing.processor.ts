import { Processor, Process } from '@nestjs/bull';
import { Logger } from '@nestjs/common';
import { Job } from 'bull';
import { McpService } from '../../mcp/mcp.service';
import { LeadsService } from '../../leads/leads.service';
import { ProcessingStage } from '../../../shared/types/nellia.types';

export interface LeadProcessingJobData {
  leadId: string;
  stage: ProcessingStage;
  retryCount?: number;
}

export interface BulkProcessingJobData {
  leadIds: string[];
}

@Processor('lead-processing')
export class LeadProcessingProcessor {
  private readonly logger = new Logger(LeadProcessingProcessor.name);

  constructor(
    private readonly mcpService: McpService,
    private readonly leadsService: LeadsService,
  ) {}

  @Process('process-lead')
  async handleLeadProcessing(job: Job<LeadProcessingJobData>) {
    const { leadId, stage, retryCount = 0 } = job.data;
    
    this.logger.log(`Processing lead ${leadId} at stage ${stage} (attempt ${retryCount + 1})`);

    try {
      // Get the lead data
      const lead = await this.leadsService.findOne(leadId);
      if (!lead) {
        throw new Error(`Lead ${leadId} not found`);
      }

      // Convert Lead entity to LeadData format manually
      const leadData = {
        id: lead.id,
        company_name: lead.company_name,
        website: lead.website,
        relevance_score: lead.relevance_score,
        roi_potential_score: lead.roi_potential_score,
        brazilian_market_fit: lead.brazilian_market_fit,
        qualification_tier: lead.qualification_tier,
        company_sector: lead.company_sector,
        persona: lead.persona,
        pain_point_analysis: lead.pain_point_analysis,
        purchase_triggers: lead.purchase_triggers,
        processing_stage: lead.processing_stage,
        created_at: lead.created_at.toISOString(),
        updated_at: lead.updated_at.toISOString(),
      };

      // Process using MCP service
      const result = await this.mcpService.processLead(leadData);
      await this.mcpService.updateLeadStage(leadId, stage);
      
      // Update lead with next stage
      const nextStage = this.getNextStage(stage);
      await this.leadsService.update(leadId, {
        processing_stage: nextStage,
      });
      
      this.logger.log(`Successfully processed lead ${leadId} at stage ${stage}`);
      
      // Schedule next stage if not complete
      if (nextStage !== 'desqualificado' && nextStage !== 'reuniao_agendada') {
        await job.queue.add('process-lead', {
          leadId,
          stage: nextStage,
        }, {
          delay: 2000, // 2 second delay between stages
        });
      }

    } catch (error) {
      this.logger.error(`Failed to process lead ${leadId} at stage ${stage}`, error.stack);
      throw error;
    }
  }

  @Process('bulk-process-leads')
  async handleBulkLeadProcessing(job: Job<BulkProcessingJobData>) {
    const { leadIds } = job.data;
    
    this.logger.log(`Starting bulk processing for ${leadIds.length} leads`);

    const results = [];
    for (const leadId of leadIds) {
      try {
        // Add individual processing job for each lead using the correct job type
        const processingQueue = job.queue as any; // Type assertion for queue access
        await processingQueue.add('process-lead', {
          leadId,
          stage: 'lead_qualification' as ProcessingStage,
        });
        
        results.push({ leadId, status: 'queued' });
      } catch (error) {
        this.logger.error(`Failed to queue lead ${leadId}`, error.stack);
        results.push({ leadId, status: 'failed', error: error.message });
      }
    }

    this.logger.log(`Bulk processing initiated: ${results.length} leads processed`);
    return results;
  }

  private getNextStage(currentStage: ProcessingStage): ProcessingStage {
    switch (currentStage) {
      case 'lead_qualification':
        return 'analyzing_refining';
      case 'analyzing_refining':
        return 'possibly_qualified';
      case 'possibly_qualified':
        return 'prospecting';
      case 'prospecting':
        return 'primeiras_mensagens';
      case 'primeiras_mensagens':
        return 'negociando';
      case 'negociando':
        return 'reuniao_agendada';
      case 'revisando':
        return 'possibly_qualified';
      default:
        return 'desqualificado';
    }
  }
}