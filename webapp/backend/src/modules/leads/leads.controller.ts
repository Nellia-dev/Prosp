import { Controller, Get, Post, Body, Patch, Param, Delete, Query } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiParam, ApiQuery } from '@nestjs/swagger';
import { LeadsService } from './leads.service';
import { 
  LeadData, 
  CreateLeadDto, 
  UpdateLeadDto, 
  LeadFilters 
} from '../../shared/types/nellia.types';

@ApiTags('leads')
@Controller('leads')
export class LeadsController {
  constructor(private readonly leadsService: LeadsService) {}

  @Get()
  @ApiOperation({ summary: 'Get all leads with optional filters' })
  @ApiResponse({ status: 200, description: 'List of leads with pagination info' })
  async findAll(@Query() filters?: LeadFilters): Promise<{ data: LeadData[], total: number }> {
    return this.leadsService.findAll(filters);
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
      marketFit: number;
    };
  }> {
    return this.leadsService.getLeadsStats();
  }
}
