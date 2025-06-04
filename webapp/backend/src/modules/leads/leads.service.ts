import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, FindManyOptions, Like, Between, In } from 'typeorm';
import { Lead } from '../../database/entities/lead.entity';
import { McpService } from '../mcp/mcp.service';
import { 
  LeadData, 
  ProcessingStage, 
  QualificationTier, 
  CreateLeadDto, 
  UpdateLeadDto, 
  LeadFilters 
} from '../../shared/types/nellia.types';

// Helper function to convert Lead entity to LeadData interface
function leadToLeadData(lead: Lead): LeadData {
  return {
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
}

@Injectable()
export class LeadsService {
  constructor(
    @InjectRepository(Lead)
    private leadRepository: Repository<Lead>,
    private mcpService: McpService,
  ) {}

  async findAll(filters?: LeadFilters): Promise<Lead[]> {
    const options: FindManyOptions<Lead> = {
      order: { created_at: 'DESC' },
    };

    if (filters) {
      const where: any = {};

      if (filters.search) {
        where.company_name = Like(`%${filters.search}%`);
      }

      if (filters.company_sector) {
        where.company_sector = filters.company_sector;
      }

      if (filters.qualification_tier) {
        where.qualification_tier = filters.qualification_tier;
      }

      if (filters.processing_stage) {
        where.processing_stage = filters.processing_stage;
      }

      if (filters.score_range) {
        where.relevance_score = Between(filters.score_range.min, filters.score_range.max);
      }

      options.where = where;
    }

    return this.leadRepository.find(options);
  }

  async findOne(id: string): Promise<Lead> {
    const lead = await this.leadRepository.findOne({ where: { id } });
    if (!lead) {
      throw new NotFoundException(`Lead with ID ${id} not found`);
    }
    return lead;
  }

  async create(createLeadDto: CreateLeadDto): Promise<Lead> {
    const lead = this.leadRepository.create({
      ...createLeadDto,
      processing_stage: 'lead_qualification' as ProcessingStage,
    });

    const savedLead = await this.leadRepository.save(lead);

    // Trigger lead processing via MCP
    try {
      await this.mcpService.processLead(leadToLeadData(savedLead));
    } catch (error) {
      console.error(`Failed to trigger MCP processing for lead ${savedLead.id}:`, error);
    }

    return savedLead;
  }

  async update(id: string, updateLeadDto: UpdateLeadDto): Promise<Lead> {
    const lead = await this.findOne(id);
    
    Object.assign(lead, updateLeadDto);
    lead.updated_at = new Date();

    return this.leadRepository.save(lead);
  }

  async remove(id: string): Promise<boolean> {
    const lead = await this.findOne(id);
    await this.leadRepository.remove(lead);
    return true;
  }

  async updateStage(id: string, stage: ProcessingStage): Promise<Lead> {
    const lead = await this.findOne(id);
    lead.processing_stage = stage;
    lead.updated_at = new Date();

    // Notify MCP of stage change
    try {
      await this.mcpService.updateLeadStage(id, stage);
    } catch (error) {
      console.error(`Failed to notify MCP of stage change for lead ${id}:`, error);
    }

    return this.leadRepository.save(lead);
  }

  async getLeadsByStage(): Promise<{ [key: string]: Lead[] }> {
    const stages: ProcessingStage[] = ['lead_qualification', 'analyzing_refining', 'possibly_qualified', 'prospecting', 'revisando', 'primeiras_mensagens', 'negociando', 'desqualificado', 'reuniao_agendada'];
    const result: { [key: string]: Lead[] } = {};

    for (const stage of stages) {
      result[stage] = await this.leadRepository.find({
        where: { processing_stage: stage },
        order: { created_at: 'DESC' },
      });
    }

    return result;
  }

  async getAnalytics() {
    const totalLeads = await this.leadRepository.count();
    
    const stageStats = await Promise.all(
      (['lead_qualification', 'analyzing_refining', 'possibly_qualified', 'prospecting', 'revisando', 'primeiras_mensagens', 'negociando', 'desqualificado', 'reuniao_agendada'] as ProcessingStage[]).map(async (stage) => {
        const count = await this.leadRepository.count({ 
          where: { processing_stage: stage } 
        });
        return { stage, count };
      })
    );

    const qualificationStats = await Promise.all(
      (['High Potential', 'Medium Potential', 'Low Potential'] as QualificationTier[]).map(async (tier) => {
        const count = await this.leadRepository.count({ 
          where: { qualification_tier: tier } 
        });
        return { tier, count };
      })
    );

    return {
      total: totalLeads,
      byStage: stageStats,
      byQualification: qualificationStats,
    };
  }

  async processLead(id: string): Promise<boolean> {
    const lead = await this.findOne(id);
    
    try {
      await this.mcpService.processLead(leadToLeadData(lead));
      return true;
    } catch (error) {
      console.error(`Failed to process lead ${id}:`, error);
      return false;
    }
  }

  async processBulk(leadIds: string[]): Promise<{ success: number; failed: number }> {
    let success = 0;
    let failed = 0;

    for (const leadId of leadIds) {
      try {
        const result = await this.processLead(leadId);
        if (result) {
          success++;
        } else {
          failed++;
        }
      } catch (error) {
        failed++;
        console.error(`Failed to process lead ${leadId}:`, error);
      }
    }

    return { success, failed };
  }

  async createBulk(createLeadDtos: CreateLeadDto[]): Promise<Lead[]> {
    const leads = createLeadDtos.map(dto => 
      this.leadRepository.create({
        ...dto,
        processing_stage: 'lead_qualification' as ProcessingStage,
      })
    );

    const savedLeads = await this.leadRepository.save(leads);

    // Trigger processing for each lead
    for (const lead of savedLeads) {
      try {
        await this.mcpService.processLead(leadToLeadData(lead));
      } catch (error) {
        console.error(`Failed to trigger MCP processing for lead ${lead.id}:`, error);
      }
    }

    return savedLeads;
  }
}
