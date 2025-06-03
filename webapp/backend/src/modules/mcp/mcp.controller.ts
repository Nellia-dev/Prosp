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
}
