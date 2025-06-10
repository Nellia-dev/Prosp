import { Injectable, NotFoundException, Inject, forwardRef } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { BusinessContextEntity } from '../../database/entities/business-context.entity';
import { McpService } from '../mcp/mcp.service';
import { 
  BusinessContext as BusinessContextType,
  CreateBusinessContextDto,
  UpdateBusinessContextDto
} from '../../shared/types/nellia.types';

@Injectable()
export class BusinessContextService {
  constructor(
    @InjectRepository(BusinessContextEntity)
    private businessContextRepository: Repository<BusinessContextEntity>,
    @Inject(forwardRef(() => McpService))
    private mcpService: McpService,
  ) {}

  async findOneByUserId(userId: string): Promise<BusinessContextEntity | null> {
    return this.businessContextRepository.findOne({
      where: { userId },
      order: { updated_at: 'DESC' },
    });
  }

  async create(userId: string, createBusinessContextDto: CreateBusinessContextDto): Promise<BusinessContextEntity> {
    const existing = await this.findOneByUserId(userId);
    if (existing) {
      return this.update(userId, createBusinessContextDto);
    }

    const contextData = { ...createBusinessContextDto };
    for (const key in contextData) {
      if (contextData[key] === undefined) {
        contextData[key] = null;
      }
    }

    const businessContext = this.businessContextRepository.create({
      ...contextData,
      userId,
    });
    const saved = await this.businessContextRepository.save(businessContext);

    try {
      await this.mcpService.updateBusinessContext(this.entityToDto(saved));
    } catch (error) {
      console.error('Failed to sync business context with MCP:', error);
    }

    return saved;
  }

  async update(userId: string, updateBusinessContextDto: UpdateBusinessContextDto): Promise<BusinessContextEntity> {
    let businessContext = await this.findOneByUserId(userId);
    
    if (!businessContext) {
      businessContext = this.businessContextRepository.create({
        ...updateBusinessContextDto,
        userId,
      });
    } else {
      const updateData = { ...updateBusinessContextDto };
      for (const key in updateData) {
        if (updateData[key] === undefined) {
          delete updateData[key];
        }
      }
      Object.assign(businessContext, updateData);
      businessContext.updated_at = new Date();
    }

    const saved = await this.businessContextRepository.save(businessContext);

    try {
      await this.mcpService.updateBusinessContext(this.entityToDto(saved));
    } catch (error) {
      console.error('Failed to sync business context with MCP:', error);
    }

    return saved;
  }

  async remove(userId: string): Promise<boolean> {
    const businessContext = await this.findOneByUserId(userId);
    if (!businessContext) {
      throw new NotFoundException(`Business context for user ${userId} not found`);
    }

    await this.businessContextRepository.remove(businessContext);

    try {
      await this.mcpService.updateBusinessContext(null);
    } catch (error) {
      console.error('Failed to clear business context in MCP:', error);
    }

    return true;
  }

  async validateContext(context: BusinessContextType): Promise<{ valid: boolean; invalidFields: string[] }> {
    const invalidFields: string[] = [];

    if (!context.business_description || context.business_description.trim().length < 10) {
      invalidFields.push('business_description');
    }

    if (!context.target_market || context.target_market.trim().length < 5) {
      invalidFields.push('target_market');
    }

    if (!context.value_proposition || context.value_proposition.trim().length < 10) {
      invalidFields.push('value_proposition');
    }

    if (!context.pain_points || context.pain_points.length === 0) {
      invalidFields.push('pain_points');
    }

    if (!context.industry_focus || context.industry_focus.length === 0) {
      invalidFields.push('industry_focus');
    }

    return {
      valid: invalidFields.length === 0,
      invalidFields,
    };
  }

  async isReadyForProspecting(userId: string): Promise<{
    ready: boolean;
    missingFields: string[];
    contextExists: boolean;
  }> {
    const contextEntity = await this.findOneByUserId(userId);
    
    if (!contextEntity) {
      return {
        ready: false,
        missingFields: ['business_description', 'product_service_description', 'target_market', 'value_proposition'],
        contextExists: false
      };
    }
  
    const contextDto = this.entityToDto(contextEntity);
    const validation = await this.validateContext(contextDto);
    
    return {
      ready: validation.valid,
      missingFields: validation.invalidFields,
      contextExists: true
    };
  }

  async getContextForMcp(userId: string): Promise<BusinessContextType | null> {
    const entity = await this.findOneByUserId(userId);
    return entity ? this.entityToDto(entity) : null;
  }

  private entityToDto(entity: BusinessContextEntity): BusinessContextType {
    return {
      id: entity.id,
      userId: entity.userId,
      business_description: entity.business_description,
      product_service_description: entity.product_service_description,
      target_market: entity.target_market,
      value_proposition: entity.value_proposition,
      ideal_customer: entity.ideal_customer,
      pain_points: entity.pain_points,
      competitors: entity.competitors,
      industry_focus: entity.industry_focus,
      competitive_advantage: entity.competitive_advantage,
      geographic_focus: entity.geographic_focus,
      is_active: entity.is_active,
      created_at: entity.created_at.toISOString(),
      updated_at: entity.updated_at.toISOString(),
    };
  }
}
