import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { AxiosResponse } from 'axios';
import { firstValueFrom } from 'rxjs';
import { AgentMetrics, AgentName, LeadData, ProcessingStage } from '../../shared/types/nellia.types';

// MCP Server API Types (matching prospect/mcp-server Flask API)
interface LeadProcessingStateCreate {
  lead_id: string;
  run_id: string;
  url?: string;
  start_time?: string;
  current_agent?: string;
}

interface AgentEventPayload {
  agent_name: string;
  status: 'SUCCESS' | 'FAILED';
  start_time: string;
  end_time: string;
  processing_time_seconds?: number;
  output_json?: string;
  metrics_json?: string;
  error_message?: string;
}

interface McpApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
}

interface LeadStatus {
  lead_status: any;
  agent_executions: any[];
}

interface RunStatus {
  run_id: string;
  leads: any[];
}

@Injectable()
export class McpService implements OnModuleInit {
  private readonly logger = new Logger(McpService.name);
  private readonly baseUrl: string;
  private readonly timeout: number;

  constructor(
    private readonly configService: ConfigService,
    private readonly httpService: HttpService,
  ) {
    this.baseUrl = this.configService.get('MCP_SERVER_URL', 'http://localhost:5001');
    this.timeout = this.configService.get('MCP_SERVER_TIMEOUT', 30000);
  }

  async onModuleInit() {
    await this.checkServerHealth();
  }

  /**
   * Check if MCP server is healthy and reachable
   */
  private async checkServerHealth(): Promise<void> {
    try {
      const response = await firstValueFrom(
        this.httpService.get(`${this.baseUrl}/health`, {
          timeout: 5000,
        })
      );
      this.logger.log('MCP server is healthy and reachable');
    } catch (error) {
      this.logger.warn('MCP server health check failed - server may not be running');
      this.logger.warn(`Make sure MCP server is running at ${this.baseUrl}`);
    }
  }

  /**
   * Generic HTTP request handler with error handling
   */
  private async makeRequest<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    endpoint: string,
    data?: any,
  ): Promise<T> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      let response: AxiosResponse<T>;

      switch (method) {
        case 'GET':
          response = await firstValueFrom(
            this.httpService.get(url, { timeout: this.timeout })
          );
          break;
        case 'POST':
          response = await firstValueFrom(
            this.httpService.post(url, data, { timeout: this.timeout })
          );
          break;
        case 'PUT':
          response = await firstValueFrom(
            this.httpService.put(url, data, { timeout: this.timeout })
          );
          break;
        case 'DELETE':
          response = await firstValueFrom(
            this.httpService.delete(url, { timeout: this.timeout })
          );
          break;
      }

      return response.data;
    } catch (error) {
      this.logger.error(`MCP API request failed: ${method} ${endpoint}`, error.message);
      throw new Error(`MCP server request failed: ${error.message}`);
    }
  }

  // =====================================
  // Lead Processing Methods (Core MCP API)
  // =====================================

  /**
   * Start lead processing - corresponds to POST /api/lead/start
   */
  async startLeadProcessing(leadProcessingData: LeadProcessingStateCreate): Promise<any> {
    return this.makeRequest('POST', '/api/lead/start', leadProcessingData);
  }

  /**
   * Record agent event - corresponds to POST /api/lead/{lead_id}/event
   */
  async recordAgentEvent(leadId: string, eventPayload: AgentEventPayload): Promise<any> {
    return this.makeRequest('POST', `/api/lead/${leadId}/event`, eventPayload);
  }

  /**
   * Get lead status - corresponds to GET /api/lead/{lead_id}/status
   */
  async getLeadStatus(leadId: string): Promise<LeadStatus> {
    return this.makeRequest('GET', `/api/lead/${leadId}/status`);
  }

  /**
   * Get run status - corresponds to GET /api/run/{run_id}/status
   */
  async getRunStatus(runId: string): Promise<RunStatus> {
    return this.makeRequest('GET', `/api/run/${runId}/status`);
  }

  // =====================================
  // Legacy Methods (Adapted for HTTP)
  // =====================================

  /**
   * Process lead - triggers processing and returns status
   */
  async processLead(leadData: LeadData): Promise<LeadData> {
    try {
      // Generate unique IDs for tracking
      const leadId = `lead_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const runId = `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      // Start lead processing in MCP server
      const processingState: LeadProcessingStateCreate = {
        lead_id: leadId,
        run_id: runId,
        url: leadData.website,
        start_time: new Date().toISOString(),
        current_agent: 'LeadIntakeAgent',
      };

      const result = await this.startLeadProcessing(processingState);
      
      // Return enhanced lead data with tracking information
      return {
        ...leadData,
        id: leadId,
        // Note: runId is not part of LeadData interface, storing in processing_stage for now
        processing_stage: 'lead_qualification' as ProcessingStage,
      } as LeadData;
    } catch (error) {
      this.logger.error('Failed to process lead', error);
      throw error;
    }
  }

  /**
   * Get lead progress - gets current processing status
   */
  async getLeadProgress(leadId: string): Promise<any> {
    try {
      const status = await this.getLeadStatus(leadId);
      return {
        leadId,
        status: status.lead_status.status,
        currentAgent: status.lead_status.current_agent,
        startTime: status.lead_status.start_time,
        lastUpdate: status.lead_status.last_update_time,
        endTime: status.lead_status.end_time,
        agentExecutions: status.agent_executions,
        errorMessage: status.lead_status.error_message,
      };
    } catch (error) {
      this.logger.error(`Failed to get lead progress for ${leadId}`, error);
      throw error;
    }
  }

  /**
   * Update lead stage - records agent completion
   */
  async updateLeadStage(leadId: string, stage: string, agentName?: string): Promise<void> {
    try {
      const eventPayload: AgentEventPayload = {
        agent_name: agentName || stage,
        status: 'SUCCESS',
        start_time: new Date().toISOString(),
        end_time: new Date().toISOString(),
        processing_time_seconds: 1.0,
        output_json: JSON.stringify({ stage, status: 'completed' }),
      };

      await this.recordAgentEvent(leadId, eventPayload);
    } catch (error) {
      this.logger.error(`Failed to update lead stage for ${leadId}`, error);
      throw error;
    }
  }

  // =====================================
  // Agent Management Methods (Simulated)
  // =====================================

  async startAgent(agentName: AgentName): Promise<void> {
    this.logger.log(`Agent management not directly supported in HTTP MCP server. Agent: ${agentName}`);
    // Could be extended to track agent states locally or via additional API
  }

  async stopAgent(agentName: AgentName): Promise<void> {
    this.logger.log(`Agent management not directly supported in HTTP MCP server. Agent: ${agentName}`);
  }

  async getAgentMetrics(agentName: AgentName): Promise<AgentMetrics> {
    // Return mock metrics - could be enhanced to aggregate from MCP server data
    return {
      processing_time_seconds: 0,
      llm_usage: {
        total_tokens: 0,
        prompt_tokens: 0,
        completion_tokens: 0,
      },
      success_rate: 100,
      queue_depth: 0,
      throughput_per_hour: 0,
    };
  }

  async getAgentStatus(agentName: AgentName): Promise<string> {
    return 'active'; // Simplified status
  }

  // =====================================
  // Chat Methods (Not implemented in MCP server)
  // =====================================

  async sendChatMessage(agentName: AgentName, message: string): Promise<string> {
    this.logger.warn('Chat functionality not implemented in current MCP server');
    return `Message received by ${agentName}: ${message}`;
  }

  // =====================================
  // Business Context Methods (Not implemented)
  // =====================================

  async updateBusinessContext(context: any): Promise<void> {
    this.logger.warn('Business context functionality not implemented in current MCP server');
  }

  async getBusinessContext(): Promise<any> {
    this.logger.warn('Business context functionality not implemented in current MCP server');
    return {};
  }

  // =====================================
  // System Methods
  // =====================================

  async ping(): Promise<boolean> {
    try {
      await this.makeRequest('GET', '/health');
      return true;
    } catch (error) {
      return false;
    }
  }

  async getSystemStatus(): Promise<any> {
    try {
      // Return basic system status
      return {
        status: 'healthy',
        serverUrl: this.baseUrl,
        timestamp: new Date().toISOString(),
        connected: true,
      };
    } catch (error) {
      return {
        status: 'error',
        serverUrl: this.baseUrl,
        timestamp: new Date().toISOString(),
        connected: false,
        error: error.message,
      };
    }
  }

  // =====================================
  // Health Check & Connection Status
  // =====================================

  isConnected(): boolean {
    // For HTTP, we consider it "connected" if the base URL is configured
    return !!this.baseUrl;
  }

  async disconnect(): Promise<void> {
    this.logger.log('HTTP MCP service does not maintain persistent connections');
  }

  /**
   * Test connection to MCP server
   */
  async testConnection(): Promise<boolean> {
    try {
      await this.ping();
      return true;
    } catch (error) {
      this.logger.error('MCP server connection test failed', error);
      return false;
    }
  }
}
