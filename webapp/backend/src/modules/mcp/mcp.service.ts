import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as WebSocket from 'ws';
import { AgentMetrics, AgentName, LeadData, McpRequest, McpResponse } from '../../shared/types/nellia.types';

@Injectable()
export class McpService implements OnModuleInit {
  private readonly logger = new Logger(McpService.name);
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 5000; // 5 seconds
  private requestId = 0;
  private pendingRequests = new Map<string, { resolve: Function; reject: Function; timeout: NodeJS.Timeout }>();

  constructor(private readonly configService: ConfigService) {}

  async onModuleInit() {
    await this.connect();
  }

  private async connect(): Promise<void> {
    const mcpServerUrl = this.configService.get('MCP_SERVER_URL', 'ws://localhost:8080');
    
    try {
      this.logger.log(`Connecting to MCP server at ${mcpServerUrl}`);
      
      this.ws = new WebSocket(mcpServerUrl);

      this.ws.on('open', () => {
        this.logger.log('Connected to MCP server');
        this.reconnectAttempts = 0;
      });

      this.ws.on('message', (data: WebSocket.Data) => {
        try {
          const response: McpResponse = JSON.parse(data.toString());
          this.handleResponse(response);
        } catch (error) {
          this.logger.error('Failed to parse MCP response:', error);
        }
      });

      this.ws.on('close', () => {
        this.logger.warn('Connection to MCP server closed');
        this.handleDisconnection();
      });

      this.ws.on('error', (error) => {
        this.logger.error('MCP WebSocket error:', error);
        this.handleDisconnection();
      });

    } catch (error) {
      this.logger.error('Failed to connect to MCP server:', error);
      this.handleDisconnection();
    }
  }

  private handleDisconnection(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      this.logger.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${this.reconnectInterval}ms`);
      
      setTimeout(() => {
        this.connect();
      }, this.reconnectInterval);
    } else {
      this.logger.error('Max reconnection attempts reached. MCP service unavailable.');
      // Clear pending requests
      this.pendingRequests.forEach(({ reject, timeout }) => {
        clearTimeout(timeout);
        reject(new Error('MCP server connection lost'));
      });
      this.pendingRequests.clear();
    }
  }

  private handleResponse(response: McpResponse): void {
    if (response.id) {
      const pending = this.pendingRequests.get(response.id);
      if (pending) {
        clearTimeout(pending.timeout);
        this.pendingRequests.delete(response.id);
        
        if (response.error) {
          pending.reject(new Error(`MCP Error: ${response.error.message}`));
        } else {
          pending.resolve(response.result);
        }
      }
    }
  }

  private async sendRequest(method: string, params?: any): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('MCP server not connected'));
        return;
      }

      const id = (++this.requestId).toString();
      const request: McpRequest = {
        id,
        method,
        params,
      };

      // Set timeout for request
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error('MCP request timeout'));
      }, 30000); // 30 seconds timeout

      this.pendingRequests.set(id, { resolve, reject, timeout });

      try {
        this.ws.send(JSON.stringify(request));
      } catch (error) {
        clearTimeout(timeout);
        this.pendingRequests.delete(id);
        reject(error);
      }
    });
  }

  // Agent Management Methods
  async startAgent(agentName: AgentName): Promise<void> {
    await this.sendRequest('agent.start', { name: agentName });
  }

  async stopAgent(agentName: AgentName): Promise<void> {
    await this.sendRequest('agent.stop', { name: agentName });
  }

  async getAgentMetrics(agentName: AgentName): Promise<AgentMetrics> {
    return await this.sendRequest('agent.metrics', { name: agentName });
  }

  async getAgentStatus(agentName: AgentName): Promise<string> {
    return await this.sendRequest('agent.status', { name: agentName });
  }

  // Lead Processing Methods
  async processLead(leadData: LeadData): Promise<LeadData> {
    return await this.sendRequest('lead.process', { lead: leadData });
  }

  async getLeadProgress(leadId: string): Promise<any> {
    return await this.sendRequest('lead.progress', { leadId });
  }

  async updateLeadStage(leadId: string, stage: string): Promise<void> {
    await this.sendRequest('lead.updateStage', { leadId, stage });
  }

  // Chat Methods
  async sendChatMessage(agentName: AgentName, message: string): Promise<string> {
    return await this.sendRequest('chat.send', { 
      agent: agentName, 
      message 
    });
  }

  // Business Context Methods
  async updateBusinessContext(context: any): Promise<void> {
    await this.sendRequest('context.update', { context });
  }

  async getBusinessContext(): Promise<any> {
    return await this.sendRequest('context.get');
  }

  // System Methods
  async ping(): Promise<boolean> {
    try {
      await this.sendRequest('system.ping');
      return true;
    } catch (error) {
      return false;
    }
  }

  async getSystemStatus(): Promise<any> {
    return await this.sendRequest('system.status');
  }

  // Health Check
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  async disconnect(): Promise<void> {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
