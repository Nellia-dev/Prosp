import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Body,
  HttpStatus,
  HttpException,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBody } from '@nestjs/swagger';
import { BusinessContextService } from './business-context.service';
import {
  CreateBusinessContextDto,
  UpdateBusinessContextDto,
  BusinessContext as BusinessContextType,
} from '../../shared/types/nellia.types';

@ApiTags('business-context')
@Controller('business-context')
export class BusinessContextController {
  constructor(private readonly businessContextService: BusinessContextService) {}

  @Get()
  @ApiOperation({ summary: 'Get business context' })
  @ApiResponse({
    status: 200,
    description: 'Business context retrieved successfully',
  })
  @ApiResponse({
    status: 404,
    description: 'Business context not found',
  })
  async getBusinessContext(): Promise<BusinessContextType | null> {
    const entity = await this.businessContextService.findOne();
    if (!entity) {
      return null;
    }

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

  @Post()
  @ApiOperation({ summary: 'Create business context' })
  @ApiBody({})
  @ApiResponse({
    status: 201,
    description: 'Business context created successfully',
  })
  @ApiResponse({
    status: 400,
    description: 'Invalid business context data',
  })
  async createBusinessContext(
    @Body() createBusinessContextDto: CreateBusinessContextDto,
  ): Promise<BusinessContextType> {
    // Validate the business context
    const validation = await this.businessContextService.validateContext(
      createBusinessContextDto as BusinessContextType,
    );

    if (!validation.valid) {
      throw new HttpException(
        {
          status: HttpStatus.BAD_REQUEST,
          error: 'Validation failed',
          message: validation.errors,
        },
        HttpStatus.BAD_REQUEST,
      );
    }

    const entity = await this.businessContextService.create(createBusinessContextDto);

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

  @Put()
  @ApiOperation({ summary: 'Update business context' })
  @ApiBody({})
  @ApiResponse({
    status: 200,
    description: 'Business context updated successfully',
  })
  @ApiResponse({
    status: 400,
    description: 'Invalid business context data',
  })
  async updateBusinessContext(
    @Body() updateBusinessContextDto: UpdateBusinessContextDto,
  ): Promise<BusinessContextType> {
    const entity = await this.businessContextService.update(updateBusinessContextDto);

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

  @Delete()
  @ApiOperation({ summary: 'Delete business context' })
  @ApiResponse({
    status: 200,
    description: 'Business context deleted successfully',
  })
  @ApiResponse({
    status: 404,
    description: 'Business context not found',
  })
  async deleteBusinessContext(): Promise<{ success: boolean }> {
    const success = await this.businessContextService.remove();
    return { success };
  }

  @Post('validate')
  @ApiOperation({ summary: 'Validate business context' })
  @ApiBody({})
  @ApiResponse({
    status: 200,
    description: 'Validation result',
  })
  async validateBusinessContext(
    @Body() businessContext: BusinessContextType,
  ): Promise<{ valid: boolean; errors: string[] }> {
    return this.businessContextService.validateContext(businessContext);
  }
}
