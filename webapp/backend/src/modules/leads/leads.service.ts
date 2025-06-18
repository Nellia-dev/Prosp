import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Lead } from '@/database/entities/lead.entity';
import { UserSeenLead } from '@/database/entities/user-seen-lead.entity';
import { QualificationTier, ProcessingStage, LeadStatus } from '@/shared/enums/nellia.enums';
import {
  LeadData,
  CreateLeadDto,
  UpdateLeadDto,
  LeadFilters
} from '../../shared/types/nellia.types';

@Injectable()
export class LeadsService {
  private readonly logger = new Logger(LeadsService.name); // Added logger instance

  constructor(
    @InjectRepository(Lead)
    private readonly leadRepository: Repository<Lead>,
    @InjectRepository(UserSeenLead) // Added
    private readonly userSeenLeadRepository: Repository<UserSeenLead>, // Added
  ) { }

  async findAll(userId: string, filters?: LeadFilters): Promise<{ data: LeadData[], total: number }> {
    this.logger.log(`Finding all leads for user ${userId} with filters: ${JSON.stringify(filters)}`);
    try {
      const query = this.leadRepository.createQueryBuilder('lead');

      // Apply filters
      if (filters) {
        if (filters.search) {
          query.andWhere(
            '(lead.company_name ILIKE :search OR lead.website ILIKE :search OR lead.company_sector ILIKE :search)',
            { search: `%${filters.search}%` }
          );
        }

        if (filters.company_sector) {
          query.andWhere('lead.company_sector = :sector', { sector: filters.company_sector });
        }

        if (filters.qualification_tier) {
          query.andWhere('lead.qualification_tier = :tier', { tier: filters.qualification_tier });
        }

        if (filters.processing_stage) {
          query.andWhere('lead.processing_stage = :stage', { stage: filters.processing_stage });
        }

        if (filters.score_range) {
          query.andWhere('lead.relevance_score BETWEEN :min AND :max', {
            min: filters.score_range.min,
            max: filters.score_range.max,
          });
        }

        // Sorting
        if (filters.sort_by) {
          const order = filters.sort_order?.toUpperCase() === 'DESC' ? 'DESC' : 'ASC';
          query.orderBy(`lead.${filters.sort_by}`, order);
        } else {
          query.orderBy('lead.created_at', 'DESC');
        }

        // Pagination
        if (filters.limit) {
          query.take(filters.limit);
        }
        if (filters.offset) {
          query.skip(filters.offset);
        }
      } else {
        query.orderBy('lead.created_at', 'DESC');
      }

      // Get seen lead IDs for the user
      const seenLeadEntries = await this.userSeenLeadRepository.find({
        where: { userId },
        select: ['leadId'], // Only select leadId
      });
      const seenLeadIds = seenLeadEntries.map(entry => entry.leadId);

      if (seenLeadIds.length > 0) {
        query.andWhere('lead.id NOT IN (:...seenLeadIds)', { seenLeadIds });
      }

      const [leads, total] = await query.getManyAndCount();
      const data = leads.map(lead => this.convertToLeadData(lead));

      return { data: data || [], total: total || 0 };
    } catch (error) {
      this.logger.error(`Error fetching leads for user ${userId}:`, error);
      return { data: [], total: 0 }; // Always return structured response, never undefined
    }
  }

  async findOne(id: string): Promise<LeadData> {
    const lead = await this.leadRepository.findOne({ where: { id } });

    if (!lead) {
      throw new NotFoundException(`Lead with ID ${id} not found`);
    }

    return this.convertToLeadData(lead);
  }

  async findById(id: string): Promise<Lead> {
    const lead = await this.leadRepository.findOne({ where: { id } });
    if (!lead) {
      throw new NotFoundException(`Lead with ID ${id} not found`);
    }
    return lead;
  }

  async create(createLeadDto: CreateLeadDto): Promise<LeadData> {
    const lead = this.leadRepository.create({
      ...createLeadDto,
      company_name: createLeadDto.company_name,
      website: createLeadDto.website || '',
      company_sector: createLeadDto.company_sector || 'Unknown',
      description: createLeadDto.description,
      contact_email: createLeadDto.contact_email,
      contact_phone: createLeadDto.contact_phone,
      contact_role: createLeadDto.contact_role,
      market_region: createLeadDto.market_region,
      company_size: createLeadDto.company_size,
      annual_revenue: createLeadDto.annual_revenue,
      // Default values for required fields
      relevance_score: 0.5,
      roi_potential_score: 0.5,
      qualification_tier: QualificationTier.MEDIUM_POTENTIAL,
      processing_stage: ProcessingStage.LEAD_QUALIFICATION,
      status: LeadStatus.NEW,
    });

    const savedLead = await this.leadRepository.save(lead);
    return this.convertToLeadData(savedLead);
  }

  async update(id: string, updateLeadDto: UpdateLeadDto): Promise<LeadData> {
    const lead = await this.leadRepository.findOne({ where: { id } });

    if (!lead) {
      throw new NotFoundException(`Lead with ID ${id} not found`);
    }

    // Update fields
    Object.assign(lead, updateLeadDto);

    // Handle enum fields properly
    if (updateLeadDto.qualification_tier) {
      lead.qualification_tier = updateLeadDto.qualification_tier as QualificationTier;
    }

    if (updateLeadDto.processing_stage) {
      lead.processing_stage = this.mapStageToEnum(updateLeadDto.processing_stage);
    }

    lead.updated_at = new Date();

    const savedLead = await this.leadRepository.save(lead);
    return this.convertToLeadData(savedLead);
  }

  async updateStage(id: string, stage: string): Promise<LeadData> {
    const lead = await this.leadRepository.findOne({ where: { id } });

    if (!lead) {
      throw new NotFoundException(`Lead with ID ${id} not found`);
    }

    lead.processing_stage = this.mapStageToEnum(stage);
    lead.updated_at = new Date();

    const savedLead = await this.leadRepository.save(lead);
    return this.convertToLeadData(savedLead);
  }

  async updateStatus(id: string, status: LeadStatus): Promise<LeadData> {
    const lead = await this.findById(id);
    lead.status = status;
    const savedLead = await this.leadRepository.save(lead);
    return this.convertToLeadData(savedLead);
  }

  async updateEnrichmentData(id: string, enrichmentData: any): Promise<LeadData> {
    const lead = await this.findById(id);
    lead.enrichment_data = enrichmentData;
    const savedLead = await this.leadRepository.save(lead);
    return this.convertToLeadData(savedLead);
  }

  async remove(id: string): Promise<void> {
    const result = await this.leadRepository.delete(id);

    if (result.affected === 0) {
      throw new NotFoundException(`Lead with ID ${id} not found`);
    }
  }

  async findByStage(stage: ProcessingStage): Promise<LeadData[]> {
    const leads = await this.leadRepository.find({
      where: { processing_stage: stage },
      order: { created_at: 'DESC' },
    });

    return leads.map(lead => this.convertToLeadData(lead));
  }

  async findByQualificationTier(tier: QualificationTier): Promise<LeadData[]> {
    const leads = await this.leadRepository.find({
      where: { qualification_tier: tier },
      order: { relevance_score: 'DESC' },
    });

    return leads.map(lead => this.convertToLeadData(lead));
  }

  async getLeadsStats(): Promise<{
    total: number;
    byStage: Record<string, number>;
    byTier: Record<string, number>;
    averageScores: {
      relevance: number;
      roi: number;
    };
  }> {
    const [leads, totalCount] = await this.leadRepository.findAndCount();

    const byStage: Record<string, number> = {};
    const byTier: Record<string, number> = {};
    let totalRelevance = 0;
    let totalRoi = 0;

    leads.forEach(lead => {
      // Count by stage
      byStage[lead.processing_stage] = (byStage[lead.processing_stage] || 0) + 1;

      // Count by tier
      byTier[lead.qualification_tier] = (byTier[lead.qualification_tier] || 0) + 1;

      // Sum scores
      totalRelevance += Number(lead.relevance_score);
      totalRoi += Number(lead.roi_potential_score);
    });

    return {
      total: totalCount,
      byStage,
      byTier,
      averageScores: {
        relevance: totalCount > 0 ? totalRelevance / totalCount : 0,
        roi: totalCount > 0 ? totalRoi / totalCount : 0,
      },
    };
  }

  async getLeadsCountByStage(): Promise<Record<ProcessingStage, number>> {
    const stages = Object.values(ProcessingStage);
    const counts: Record<ProcessingStage, number> = {} as any;

    for (const stage of stages) {
      counts[stage] = await this.leadRepository.count({
        where: { processing_stage: stage },
      });
    }

    return counts;
  }

  // Helper method to map string stage to enum
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

  // Convert Lead entity to LeadData for API responses
  private convertToLeadData(lead: Lead): LeadData {
    console.log(`Converting lead entity to DTO: ${lead.id}`);
    const leadData = {
      id: lead.id,
      company_name: lead.company_name,
      website: lead.website,
      relevance_score: Number(lead.relevance_score),
      roi_potential_score: Number(lead.roi_potential_score),
      qualification_tier: lead.qualification_tier,
      company_sector: lead.company_sector,
      persona: lead.persona ? {
        likely_role: lead.persona.likely_role || '',
        decision_maker_probability: lead.persona.decision_maker_probability || 0,
      } : undefined,
      pain_point_analysis: lead.pain_point_analysis,
      purchase_triggers: lead.purchase_triggers,
      processing_stage: lead.processing_stage as any,
      status: lead.status,
      enrichment_data: lead.enrichment_data,
      created_at: lead.created_at.toISOString(),
      updated_at: lead.updated_at.toISOString(),
    };
    console.log(`Converted DTO:`, leadData);
    return leadData;
  }

  async markAsSeen(userId: string, leadId: string): Promise<void> {
    try {
      const existingEntry = await this.userSeenLeadRepository.findOne({
        where: { userId, leadId },
      });

      if (existingEntry) {
        // Optionally, update seenAt if it already exists, or just return
        // this.logger.log(`Lead ${leadId} already marked as seen by user ${userId}`);
        // existingEntry.seenAt = new Date();
        // await this.userSeenLeadRepository.save(existingEntry);
        return;
      }

      const userSeenLead = this.userSeenLeadRepository.create({
        userId,
        leadId,
        // seenAt is defaulted by the database
      });
      await this.userSeenLeadRepository.save(userSeenLead);
      this.logger.log(`Lead ${leadId} marked as seen by user ${userId}`);
    } catch (error) {
      // Consider if the lead or user doesn't exist, FK constraint will throw an error.
      // Specific error handling can be added if needed.
      this.logger.error(`Error marking lead ${leadId} as seen for user ${userId}:`, error);
      // Re-throw or handle as appropriate for the application
      throw error;
    }
  }
}
