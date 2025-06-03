import {
  Controller,
  Get,
  Post,
  Body,
  Patch,
  Param,
  Delete,
  Query,
  HttpStatus,
  HttpCode,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiQuery } from '@nestjs/swagger';
import { LeadsService } from './leads.service';
import {
  CreateLeadDto,
  UpdateLeadDto,
  LeadFilters,
  ProcessingStage,
} from '../../shared/types/nellia.types';

@ApiTags('leads')
@Controller('leads')
export class LeadsController {
  constructor(private readonly leadsService: LeadsService) {}

  @Post()
  @ApiOperation({ summary: 'Create a new lead' })
  @ApiResponse({ status: 201, description: 'Lead created successfully' })
  @ApiResponse({ status: 400, description: 'Bad request' })
  async create(@Body() createLeadDto: CreateLeadDto) {
    return this.leadsService.create(createLeadDto);
  }

  @Post('bulk')
  @ApiOperation({ summary: 'Create multiple leads' })
  @ApiResponse({ status: 201, description: 'Leads created successfully' })
  @ApiResponse({ status: 400, description: 'Bad request' })
  async createBulk(@Body() createLeadDtos: CreateLeadDto[]) {
    return this.leadsService.createBulk(createLeadDtos);
  }

  @Get()
  @ApiOperation({ summary: 'Get all leads with optional filtering' })
  @ApiQuery({ name: 'search', required: false, description: 'Search term for company name' })
  @ApiQuery({ name: 'company_sector', required: false, description: 'Filter by company sector' })
  @ApiQuery({ name: 'qualification_tier', required: false, description: 'Filter by qualification tier' })
  @ApiQuery({ name: 'processing_stage', required: false, description: 'Filter by processing stage' })
  @ApiQuery({ name: 'sort_by', required: false, description: 'Sort field' })
  @ApiQuery({ name: 'sort_order', required: false, description: 'Sort order (asc/desc)' })
  @ApiQuery({ name: 'limit', required: false, description: 'Number of results to return' })
  @ApiQuery({ name: 'offset', required: false, description: 'Number of results to skip' })
  async findAll(@Query() query: any) {
    const filters: LeadFilters = {
      search: query.search,
      company_sector: query.company_sector,
      qualification_tier: query.qualification_tier,
      processing_stage: query.processing_stage,
      sort_by: query.sort_by,
      sort_order: query.sort_order,
      limit: query.limit ? parseInt(query.limit) : undefined,
      offset: query.offset ? parseInt(query.offset) : undefined,
    };

    // Handle score range filter
    if (query.score_min !== undefined && query.score_max !== undefined) {
      filters.score_range = {
        min: parseFloat(query.score_min),
        max: parseFloat(query.score_max),
      };
    }

    return this.leadsService.findAll(filters);
  }

  @Get('by-stage')
  @ApiOperation({ summary: 'Get leads grouped by processing stage' })
  @ApiResponse({ status: 200, description: 'Leads grouped by stage' })
  async getLeadsByStage() {
    return this.leadsService.getLeadsByStage();
  }

  @Get('analytics')
  @ApiOperation({ summary: 'Get lead analytics and statistics' })
  @ApiResponse({ status: 200, description: 'Lead analytics data' })
  async getAnalytics() {
    return this.leadsService.getAnalytics();
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get a lead by ID' })
  @ApiResponse({ status: 200, description: 'Lead found' })
  @ApiResponse({ status: 404, description: 'Lead not found' })
  async findOne(@Param('id') id: string) {
    return this.leadsService.findOne(id);
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Update a lead' })
  @ApiResponse({ status: 200, description: 'Lead updated successfully' })
  @ApiResponse({ status: 404, description: 'Lead not found' })
  async update(@Param('id') id: string, @Body() updateLeadDto: UpdateLeadDto) {
    return this.leadsService.update(id, updateLeadDto);
  }

  @Patch(':id/stage')
  @ApiOperation({ summary: 'Update lead processing stage' })
  @ApiResponse({ status: 200, description: 'Lead stage updated successfully' })
  @ApiResponse({ status: 404, description: 'Lead not found' })
  async updateStage(
    @Param('id') id: string,
    @Body('stage') stage: ProcessingStage,
  ) {
    return this.leadsService.updateStage(id, stage);
  }

  @Post(':id/process')
  @ApiOperation({ summary: 'Trigger processing for a specific lead' })
  @ApiResponse({ status: 200, description: 'Lead processing triggered' })
  @ApiResponse({ status: 404, description: 'Lead not found' })
  @HttpCode(HttpStatus.OK)
  async processLead(@Param('id') id: string) {
    const result = await this.leadsService.processLead(id);
    return { success: result };
  }

  @Post('process-bulk')
  @ApiOperation({ summary: 'Process multiple leads' })
  @ApiResponse({ status: 200, description: 'Bulk processing initiated' })
  @HttpCode(HttpStatus.OK)
  async processBulk(@Body('leadIds') leadIds: string[]) {
    return this.leadsService.processBulk(leadIds);
  }

  @Delete(':id')
  @ApiOperation({ summary: 'Delete a lead' })
  @ApiResponse({ status: 200, description: 'Lead deleted successfully' })
  @ApiResponse({ status: 404, description: 'Lead not found' })
  async remove(@Param('id') id: string) {
    const result = await this.leadsService.remove(id);
    return { success: result };
  }
}
