import { Injectable, NotFoundException } from '@nestjs/common';
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
    private mcpService: McpService,
  ) {}

  async findOne(): Promise<BusinessContextEntity | null> {
    // Only one business context per application
    return this.businessContextRepository.findOne({
      order: { updated_at: 'DESC' },
    });
  }

  async create(createBusinessContextDto: CreateBusinessContextDto): Promise<BusinessContextEntity> {
    // Check if context already exists
    const existing = await this.findOne();
    if (existing) {
      // Update existing instead of creating new
      return this.update(createBusinessContextDto);
    }

    const businessContext = this.businessContextRepository.create(createBusinessContextDto);
    const saved = await this.businessContextRepository.save(businessContext);

    // Sync with MCP server
    try {
      await this.mcpService.updateBusinessContext(this.entityToDto(saved));
    } catch (error) {
      console.error('Failed to sync business context with MCP:', error);
    }

    return saved;
  }

  async update(updateBusinessContextDto: UpdateBusinessContextDto): Promise<BusinessContextEntity> {
    let businessContext = await this.findOne();
    
    if (!businessContext) {
      // Create new if none exists
      businessContext = this.businessContextRepository.create(updateBusinessContextDto);
    } else {
      Object.assign(businessContext, updateBusinessContextDto);
      businessContext.updated_at = new Date();
    }

    const saved = await this.businessContextRepository.save(businessContext);

    // Sync with MCP server
    try {
      await this.mcpService.updateBusinessContext(this.entityToDto(saved));
    } catch (error) {
      console.error('Failed to sync business context with MCP:', error);
    }

    return saved;
  }

  async remove(): Promise<boolean> {
    const businessContext = await this.findOne();
    if (!businessContext) {
      throw new NotFoundException('Business context not found');
    }

    await this.businessContextRepository.remove(businessContext);

    // Notify MCP server
    try {
      await this.mcpService.updateBusinessContext(null);
    } catch (error) {
      console.error('Failed to clear business context in MCP:', error);
    }

    return true;
  }

  async validateContext(context: BusinessContextType): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = [];

    if (!context.business_description || context.business_description.trim().length < 10) {
      errors.push('Business description must be at least 10 characters long');
    }

    if (!context.target_market || context.target_market.trim().length < 5) {
      errors.push('Target market must be specified');
    }

    if (!context.value_proposition || context.value_proposition.trim().length < 10) {
      errors.push('Value proposition must be at least 10 characters long');
    }

    if (!context.pain_points || context.pain_points.length === 0) {
      errors.push('At least one pain point must be specified');
    }

    if (!context.industry_focus || context.industry_focus.length === 0) {
      errors.push('At least one industry focus must be specified');
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  async getContextForMcp(): Promise<BusinessContextType | null> {
    const entity = await this.findOne();
    return entity ? this.entityToDto(entity) : null;
  }

  private entityToDto(entity: BusinessContextEntity): BusinessContextType {
    return {
      id: entity.id,
      business_description: entity.business_description,
      target_market: entity.target_market,
      value_proposition: entity.value_proposition,
      ideal_customer: entity.ideal_customer,
      pain_points: entity.pain_points,
      industry_focus: entity.industry_focus,
      created_at: entity.created_at.toISOString(),
      updated_at: entity.updated_at.toISOString(),
    };
  }
}
