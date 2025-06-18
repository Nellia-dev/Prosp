import { Controller, Get, Post, Body, Patch, Param, Delete, Query, BadRequestException } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiParam, ApiQuery, ApiBearerAuth } from '@nestjs/swagger';
import { LeadsService } from './leads.service';
import { UserId } from '../auth/user-id.decorator';
import {
  LeadData,
  CreateLeadDto,
  UpdateLeadDto,
  LeadFilters
} from '../../shared/types/nellia.types';

@ApiBearerAuth()
@ApiTags('leads')
@Controller('leads')
export class LeadsController {
  constructor(private readonly leadsService: LeadsService) { }

  @Get()
  @ApiOperation({ summary: 'Get all leads with optional filters (excludes seen leads for the user)' })
  @ApiResponse({ status: 200, description: 'List of leads with pagination info' })
  async findAll(
    @Query() filters?: LeadFilters,
    @UserId() userId?: string,
  ): Promise<{ data: LeadData[], total: number }> {
    if (!userId) {
      throw new BadRequestException('User ID is required to fetch leads.');
    }
    return this.leadsService.findAll(userId, filters);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get specific lead details' })
  @ApiParam({ name: 'id', description: 'Lead ID' })
  @ApiResponse({ status: 200, description: 'Lead details' })
  @ApiResponse({ status: 404, description: 'Lead not found' })
  async findOne(@Param('id') id: string): Promise<LeadData> {
    return this.leadsService.findOne(id);
  }

  @Post()
  @ApiOperation({ summary: 'Create a new lead' })
  @ApiResponse({ status: 201, description: 'Lead created successfully' })
  @ApiResponse({ status: 400, description: 'Invalid lead data' })
  async create(@Body() createLeadDto: CreateLeadDto): Promise<LeadData> {
    return this.leadsService.create(createLeadDto);
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Update lead details' })
  @ApiParam({ name: 'id', description: 'Lead ID' })
  @ApiResponse({ status: 200, description: 'Lead updated successfully' })
  @ApiResponse({ status: 404, description: 'Lead not found' })
  async update(@Param('id') id: string, @Body() updateLeadDto: UpdateLeadDto): Promise<LeadData> {
    return this.leadsService.update(id, updateLeadDto);
  }

  @Patch(':id/stage')
  @ApiOperation({ summary: 'Update lead processing stage' })
  @ApiParam({ name: 'id', description: 'Lead ID' })
  @ApiResponse({ status: 200, description: 'Lead stage updated successfully' })
  @ApiResponse({ status: 404, description: 'Lead not found' })
  async updateStage(
    @Param('id') id: string,
    @Body('stage') stage: string
  ): Promise<LeadData> {
    return this.leadsService.updateStage(id, stage);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Delete a lead' })
  @ApiParam({ name: 'id', description: 'Lead ID' })
  @ApiResponse({ status: 204, description: 'Lead deleted successfully' })
  @ApiResponse({ status: 404, description: 'Lead not found' })
  async remove(@Param('id') id: string): Promise<void> {
    return this.leadsService.remove(id);
  }

  @Post(':id/mark-seen')
  @ApiOperation({ summary: 'Mark a lead as seen by the current user' })
  @ApiParam({ name: 'id', description: 'Lead ID' })
  @ApiResponse({ status: 201, description: 'Lead marked as seen' }) // 201 for resource state change (creation of seen record)
  @ApiResponse({ status: 400, description: 'Invalid input: User ID or Lead ID missing' })
  @ApiResponse({ status: 404, description: 'Lead not found or user context issue' })
  async markLeadAsSeen(
    @Param('id') leadId: string,
    @UserId() userId: string,
  ): Promise<void> {
    if (!userId || !leadId) {
        throw new BadRequestException('User ID and Lead ID must be provided.');
    }
    return this.leadsService.markAsSeen(userId, leadId);
  }

  @Get('stats/summary')
  @ApiOperation({ summary: 'Get leads statistics summary' })
  @ApiResponse({ status: 200, description: 'Leads statistics' })
  async getStats(): Promise<{
    total: number;
    byStage: Record<string, number>;
    byTier: Record<string, number>;
    averageScores: {
      relevance: number;
      roi: number;
    };
  }> {
    return this.leadsService.getLeadsStats();
  }
}
