import { Controller, Get, Post, Body, Param, HttpException, HttpStatus } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiParam, ApiBody } from '@nestjs/swagger';
import { McpService } from './mcp.service';
import { AgentName } from '../../shared/types/nellia.types';

@ApiTags('MCP (Model Context Protocol)')
@Controller('mcp')
export class McpController {
  constructor(private readonly mcpService: McpService) {}

  @Get('health')
  @ApiOperation({ summary: 'Check MCP server health status' })
  @ApiResponse({ status: 200, description: 'MCP server health status' })
  async getHealth(): Promise<{ status: string; connected: boolean; lastConnected?: Date }> {
    try {
      const isConnected = this.mcpService.isConnected();
      const status = await this.mcpService.getSystemStatus();
      
      return {
        status: isConnected ? 'connected' : 'disconnected',
        connected: isConnected,
        lastConnected: status.lastConnected
      };
    } catch (error) {
      throw new HttpException(
        'Failed to get MCP health status',
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }

  @Get('status')
  @ApiOperation({ summary: 'Get detailed MCP system status' })
  @ApiResponse({ status: 200, description: 'Detailed MCP system status' })
  async getSystemStatus() {
    try {
      return await this.mcpService.getSystemStatus();
    } catch (error) {
      throw new HttpException(
        'Failed to get system status',
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }

  @Post('ping')
  @ApiOperation({ summary: 'Ping MCP server' })
  @ApiResponse({ status: 200, description: 'MCP server ping result' })
  async ping(): Promise<{ connected: boolean }> {
    try {
      const result = await this.mcpService.ping();
      return { connected: result };
    } catch (error) {
      throw new HttpException(
        'Failed to ping MCP server',
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }

  @Post('disconnect')
  @ApiOperation({ summary: 'Disconnect from MCP server' })
  @ApiResponse({ status: 200, description: 'Disconnected from MCP server' })
  async disconnect(): Promise<{ message: string }> {
    try {
      await this.mcpService.disconnect();
      return { message: 'Disconnected from MCP server' };
    } catch (error) {
      throw new HttpException(
        'Failed to disconnect',
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }

  @Get('agents/:agentId/status')
  @ApiOperation({ summary: 'Get status of a specific agent' })
  @ApiParam({ name: 'agentId', description: 'Agent identifier' })
  @ApiResponse({ status: 200, description: 'Agent status' })
  async getAgentStatus(@Param('agentId') agentId: string) {
    try {
      return await this.mcpService.getAgentStatus(agentId as AgentName);
    } catch (error) {
      throw new HttpException(
        `Failed to get status for agent ${agentId}: ${error.message}`,
        HttpStatus.BAD_REQUEST
      );
    }
  }

  @Get('agents/:agentId/metrics')
  @ApiOperation({ summary: 'Get metrics of a specific agent' })
  @ApiParam({ name: 'agentId', description: 'Agent identifier' })
  @ApiResponse({ status: 200, description: 'Agent metrics' })
  async getAgentMetrics(@Param('agentId') agentId: string) {
    try {
      return await this.mcpService.getAgentMetrics(agentId as AgentName);
    } catch (error) {
      throw new HttpException(
        `Failed to get metrics for agent ${agentId}: ${error.message}`,
        HttpStatus.BAD_REQUEST
      );
    }
  }

  @Post('agents/:agentId/start')
  @ApiOperation({ summary: 'Start a specific agent' })
  @ApiParam({ name: 'agentId', description: 'Agent identifier' })
  @ApiResponse({ status: 200, description: 'Agent started successfully' })
  async startAgent(@Param('agentId') agentId: string): Promise<{ message: string }> {
    try {
      await this.mcpService.startAgent(agentId as AgentName);
      return { message: `Agent ${agentId} started successfully` };
    } catch (error) {
      throw new HttpException(
        `Failed to start agent ${agentId}: ${error.message}`,
        HttpStatus.BAD_REQUEST
      );
    }
  }

  @Post('agents/:agentId/stop')
  @ApiOperation({ summary: 'Stop a specific agent' })
  @ApiParam({ name: 'agentId', description: 'Agent identifier' })
  @ApiResponse({ status: 200, description: 'Agent stopped successfully' })
  async stopAgent(@Param('agentId') agentId: string): Promise<{ message: string }> {
    try {
      await this.mcpService.stopAgent(agentId as AgentName);
      return { message: `Agent ${agentId} stopped successfully` };
    } catch (error) {
      throw new HttpException(
        `Failed to stop agent ${agentId}: ${error.message}`,
        HttpStatus.BAD_REQUEST
      );
    }
  }

  @Post('context/update')
  @ApiOperation({ summary: 'Update business context' })
  @ApiResponse({ status: 200, description: 'Business context updated' })
  async updateBusinessContext(@Body() context: any): Promise<{ message: string }> {
    try {
      await this.mcpService.updateBusinessContext(context);
      return { message: 'Business context updated successfully' };
    } catch (error) {
      throw new HttpException(
        `Failed to update business context: ${error.message}`,
        HttpStatus.BAD_REQUEST
      );
    }
  }

  @Get('context')
  @ApiOperation({ summary: 'Get business context' })
  @ApiResponse({ status: 200, description: 'Business context retrieved' })
  async getBusinessContext() {
    try {
      return await this.mcpService.getBusinessContext();
    } catch (error) {
      throw new HttpException(
        `Failed to get business context: ${error.message}`,
        HttpStatus.BAD_REQUEST
      );
    }
  }

  @Get('agents/all/status')
  @ApiOperation({ summary: 'Get status of all agents in the system' })
  @ApiResponse({
    status: 200,
    description: 'Status of all agents organized by category',
    schema: {
      type: 'object',
      properties: {
        statuses: {
          type: 'object',
          additionalProperties: { type: 'string' }
        },
        summary: {
          type: 'object',
          properties: {
            total: { type: 'number' },
            active: { type: 'number' },
            inactive: { type: 'number' },
            processing: { type: 'number' }
          }
        }
      }
    }
  })
  async getAllAgentStatuses() {
    try {
      const statuses = await this.mcpService.getAllAgentStatuses();
      
      // Calculate summary statistics
      const statusValues = Object.values(statuses);
      const summary = {
        total: statusValues.length,
        active: statusValues.filter(status => status === 'active').length,
        inactive: statusValues.filter(status => status === 'inactive').length,
        processing: statusValues.filter(status => status === 'processing').length,
        error: statusValues.filter(status => status === 'error').length,
      };
      
      return {
        statuses,
        summary,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      throw new HttpException(
        `Failed to get all agent statuses: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }

  @Get('agents/support/verify')
  @ApiOperation({ summary: 'Verify MCP server supports all required agents' })
  @ApiResponse({
    status: 200,
    description: 'Agent support verification results',
    schema: {
      type: 'object',
      properties: {
        supportedAgents: {
          type: 'array',
          items: { type: 'string' }
        },
        unsupportedAgents: {
          type: 'array',
          items: { type: 'string' }
        },
        totalAgents: { type: 'number' },
        supportPercentage: { type: 'number' }
      }
    }
  })
  async verifyAgentSupport() {
    try {
      const verification = await this.mcpService.verifyAgentSupport();
      return {
        ...verification,
        timestamp: new Date().toISOString(),
        status: verification.supportPercentage === 100 ? 'fully_supported' : 'partial_support'
      };
    } catch (error) {
      throw new HttpException(
        `Failed to verify agent support: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }

  @Get('agents/categories')
  @ApiOperation({ summary: 'Get all agents organized by category' })
  @ApiResponse({
    status: 200,
    description: 'All agents organized by their categories',
    schema: {
      type: 'object',
      properties: {
        initial_processing: {
          type: 'array',
          items: { type: 'string' }
        },
        orchestrator: {
          type: 'array',
          items: { type: 'string' }
        },
        specialized: {
          type: 'array',
          items: { type: 'string' }
        },
        alternative: {
          type: 'array',
          items: { type: 'string' }
        }
      }
    }
  })
  async getAgentsByCategory() {
    try {
      // Define agents by category
      const agentsByCategory = {
        initial_processing: [
          'lead_intake_agent',
          'lead_analysis_agent'
        ],
        orchestrator: [
          'enhanced_lead_processor'
        ],
        specialized: [
          'tavily_enrichment_agent',
          'contact_extraction_agent',
          'pain_point_deepening_agent',
          'lead_qualification_agent',
          'competitor_identification_agent',
          'strategic_question_generation_agent',
          'buying_trigger_identification_agent',
          'tot_strategy_generation_agent',
          'tot_strategy_evaluation_agent',
          'tot_action_plan_synthesis_agent',
          'detailed_approach_plan_agent',
          'objection_handling_agent',
          'value_proposition_customization_agent',
          'b2b_personalized_message_agent',
          'internal_briefing_summary_agent'
        ],
        alternative: [
          'approach_strategy_agent',
          'b2b_persona_creation_agent',
          'message_crafting_agent',
          'persona_creation_agent',
          'lead_analysis_generation_agent'
        ]
      };

      return {
        categories: agentsByCategory,
        summary: {
          total_agents: Object.values(agentsByCategory).flat().length,
          categories: Object.keys(agentsByCategory).length,
          agents_per_category: Object.fromEntries(
            Object.entries(agentsByCategory).map(([category, agents]) => [category, agents.length])
          )
        },
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      throw new HttpException(
        `Failed to get agents by category: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR
      );
    }
  }

  @Post('test/connection')
  @ApiOperation({ summary: 'Test connection to MCP server' })
  @ApiResponse({ status: 200, description: 'Connection test results' })
  async testConnection() {
    try {
      const isConnected = await this.mcpService.testConnection();
      const systemStatus = await this.mcpService.getSystemStatus();
      
      return {
        connected: isConnected,
        status: isConnected ? 'success' : 'failed',
        serverUrl: systemStatus.serverUrl,
        timestamp: new Date().toISOString(),
        details: systemStatus
      };
    } catch (error) {
      throw new HttpException(
        `Connection test failed: ${error.message}`,
        HttpStatus.SERVICE_UNAVAILABLE
      );
    }
  }
}
