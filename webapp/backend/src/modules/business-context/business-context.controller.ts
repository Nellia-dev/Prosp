import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Body,
  HttpStatus,
  HttpException,
  UseGuards,
  Req,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBody, ApiBearerAuth } from '@nestjs/swagger';
import { UserId } from '../auth/user-id.decorator';
import { AuthGuard } from '@nestjs/passport';
import { BusinessContextService } from './business-context.service';
import { Public } from '../auth/public.decorator';
import {
  CreateBusinessContextDto,
  UpdateBusinessContextDto,
  BusinessContext as BusinessContextType,
} from '../../shared/types/nellia.types';
import { BusinessContextEntity } from '../../database/entities/business-context.entity';

@ApiBearerAuth()
@ApiTags('business-context')
@Controller('business-context')
export class BusinessContextController {
  constructor(private readonly businessContextService: BusinessContextService) {}

  @Get()
  @ApiOperation({ summary: 'Get the business context for the authenticated user' })
  @ApiResponse({
    status: 200,
    description: 'Business context retrieved successfully.',
  })
  @ApiResponse({ status: 404, description: 'Business context not found.' })
  async getBusinessContext(@UserId() userId: string): Promise<BusinessContextType | null> {
    const entity = await this.businessContextService.findOneByUserId(userId);
    if (!entity) {
      return null;
    }
    return this.entityToDto(entity);
  }

  @Post()
  @ApiOperation({ summary: 'Create or update the business context for the authenticated user' })
  @ApiBody({ type: CreateBusinessContextDto })
  @ApiResponse({
    status: 201,
    description: 'Business context created or updated successfully.',
  })
  @ApiResponse({ status: 400, description: 'Invalid business context data.' })
  async createOrUpdateBusinessContext(
    @UserId() userId: string,
    @Body() createDto: CreateBusinessContextDto,
  ): Promise<BusinessContextType> {
    console.log('Creating or updating business context for user:', userId);
    console.log('Received DTO:', createDto);
    const validation = await this.businessContextService.validateContext(createDto as BusinessContextType);
    console.log('Validation result:', validation);
    // If validation fails, throw an exception with the invalid fields
    if (!validation.valid) {
      throw new HttpException(
        {
          status: HttpStatus.BAD_REQUEST,
          error: 'Validation failed',
          message: validation.invalidFields,
        },
        HttpStatus.BAD_REQUEST,
      );
    }
    const entity = await this.businessContextService.create(userId, createDto);
    return this.entityToDto(entity);
  }

  @Put()
  @ApiOperation({ summary: 'Update the business context for the authenticated user' })
  @ApiBody({ type: UpdateBusinessContextDto })
  @ApiResponse({
    status: 200,
    description: 'Business context updated successfully.',
  })
  async updateBusinessContext(
    @UserId() userId: string,
    @Body() updateDto: UpdateBusinessContextDto,
  ): Promise<BusinessContextType> {
    const entity = await this.businessContextService.update(userId, updateDto);
    return this.entityToDto(entity);
  }

  @Delete()
  @ApiOperation({ summary: 'Delete the business context for the authenticated user' })
  @ApiResponse({
    status: 200,
    description: 'Business context deleted successfully.',
  })
  async deleteBusinessContext(@UserId() userId: string): Promise<{ success: boolean }> {
    const success = await this.businessContextService.remove(userId);
    return { success };
  }

  @Public()
  @Post('validate')
  @ApiOperation({ summary: 'Validate business context' })
  @ApiBody({ type: CreateBusinessContextDto })
  @ApiResponse({
    status: 200,
    description: 'Validation result',
  })
  async validateBusinessContext(
    @Body() businessContext: BusinessContextType,
  ): Promise<{ valid: boolean; invalidFields: string[] }> {
    return this.businessContextService.validateContext(businessContext);
  }

  @Get('ready-for-prospecting')
  @ApiOperation({ summary: 'Check if the business context for the authenticated user is ready for prospecting' })
  @ApiResponse({
    status: 200,
    description: 'Readiness status retrieved successfully.',
  })
  async isReadyForProspecting(@UserId() userId: string): Promise<{
    ready: boolean;
    missingFields: string[];
    contextExists: boolean;
  }> {
    return this.businessContextService.isReadyForProspecting(userId);
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
      search_query: entity.search_query,
      is_active: entity.is_active,
      created_at: entity.created_at.toISOString(),
      updated_at: entity.updated_at.toISOString(),
    };
  }
}
