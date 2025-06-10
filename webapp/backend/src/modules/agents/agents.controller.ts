import { Controller, Get, Post, Param, HttpCode, HttpStatus, Query } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiParam, ApiQuery, ApiBearerAuth } from '@nestjs/swagger';
import { AgentsService } from './agents.service';
import { AgentStatus, AgentMetrics, AgentCategory } from '../../shared/types/nellia.types';

@ApiBearerAuth()
@ApiTags('agents')
@Controller('agents')
export class AgentsController {
  constructor(private readonly agentsService: AgentsService) {}

  @Get()
  @ApiOperation({ summary: 'Get all agents with their current status' })
  @ApiResponse({ status: 200, description: 'List of all agents with status and metrics' })
  async findAll(): Promise<AgentStatus[]> {
    return this.agentsService.findAll();
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get specific agent details' })
  @ApiParam({ name: 'id', description: 'Agent ID' })
  @ApiResponse({ status: 200, description: 'Agent details with status and metrics' })
  @ApiResponse({ status: 404, description: 'Agent not found' })
  async findOne(@Param('id') id: string): Promise<AgentStatus> {
    return this.agentsService.findOne(id);
  }

  @Post(':id/start')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Start an agent' })
  @ApiParam({ name: 'id', description: 'Agent ID' })
  @ApiResponse({ status: 200, description: 'Agent started successfully' })
  @ApiResponse({ status: 404, description: 'Agent not found' })
  @ApiResponse({ status: 500, description: 'Failed to start agent' })
  async startAgent(@Param('id') id: string): Promise<AgentStatus> {
    return this.agentsService.startAgent(id);
  }

  @Post(':id/stop')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Stop an agent' })
  @ApiParam({ name: 'id', description: 'Agent ID' })
  @ApiResponse({ status: 200, description: 'Agent stopped successfully' })
  @ApiResponse({ status: 404, description: 'Agent not found' })
  @ApiResponse({ status: 500, description: 'Failed to stop agent' })
  async stopAgent(@Param('id') id: string): Promise<AgentStatus> {
    return this.agentsService.stopAgent(id);
  }

  @Get(':id/metrics')
  @ApiOperation({ summary: 'Get agent performance metrics' })
  @ApiParam({ name: 'id', description: 'Agent ID' })
  @ApiResponse({ status: 200, description: 'Agent performance metrics' })
  @ApiResponse({ status: 404, description: 'Agent not found' })
  async getMetrics(@Param('id') id: string): Promise<AgentMetrics> {
    return this.agentsService.getAgentMetrics(id);
  }

  @Get('category/:category')
  @ApiOperation({ summary: 'Get agents by category' })
  @ApiParam({
    name: 'category',
    description: 'Agent category',
    enum: ['initial_processing', 'orchestrator', 'specialized', 'alternative']
  })
  @ApiResponse({ status: 200, description: 'List of agents in the specified category' })
  async findByCategory(@Param('category') category: AgentCategory): Promise<AgentStatus[]> {
    return this.agentsService.findByCategory(category);
  }

  @Get('pipeline/structure')
  @ApiOperation({ summary: 'Get all agents organized by pipeline structure' })
  @ApiResponse({
    status: 200,
    description: 'All agents organized by their role in the processing pipeline'
  })
  async getPipelineStructure(): Promise<{
    initial: AgentStatus[];
    orchestrator: AgentStatus[];
    specialized: AgentStatus[];
    alternative: AgentStatus[];
  }> {
    return this.agentsService.getAgentsByPipeline();
  }

  @Get('categories/all')
  @ApiOperation({ summary: 'Get all agents grouped by category' })
  @ApiResponse({
    status: 200,
    description: 'All agents grouped by their categories'
  })
  async getAllByCategory(): Promise<Record<AgentCategory, AgentStatus[]>> {
    return this.agentsService.getAllAgentsByCategory();
  }
}
