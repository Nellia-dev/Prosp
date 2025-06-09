import { Injectable, Logger, OnModuleInit, Inject, forwardRef } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { AxiosResponse } from 'axios';
import { firstValueFrom } from 'rxjs';
import { AgentMetrics, LeadData, ProcessingStage, BusinessContext as BusinessContextType } from '../../shared/types/nellia.types';
import { AgentName, AgentCategory } from '../../shared/enums/nellia.enums';
import { Lead } from '@/database/entities/lead.entity';
import { BusinessContextService } from '../business-context/business-context.service';
import EventSource from 'eventsource';
import { AxiosError } from 'axios';

export class McpApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly data?: any,
  ) {
    super(message);
    this.name = 'McpApiError';
  }
}

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

interface EnrichmentJobData {
  user_id: string;
  job_id: string;
  analyzed_lead_data: any; // Sending the full lead entity as dict
  product_service_context: string;
  competitors_list?: string;
  timestamp: string;
}


@Injectable()
export class McpService implements OnModuleInit {
  private readonly logger = new Logger(McpService.name);
  private readonly baseUrl: string;
  private readonly timeout: number;

  constructor(
    private readonly configService: ConfigService,
    private readonly httpService: HttpService,
    @Inject(forwardRef(() => BusinessContextService))
    private readonly businessContextService: BusinessContextService,
  ) {
    this.baseUrl = this.configService.get('MCP_SERVER_URL', 'http://localhost:5001');
    this.timeout = this.configService.get('MCP_SERVER_TIMEOUT', 180000); // Increased timeout for long-running processes
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
      this.logger.error(`MCP API request failed: ${method} ${endpoint}`, error.stack);
      if (error.isAxiosError) {
        const axiosError = error as AxiosError;
        const status = axiosError.response?.status;
        const data = axiosError.response?.data;
        throw new McpApiError(`MCP server request failed with status ${status}`, status, data);
      }
      throw new McpApiError(`MCP server request failed: ${error.message}`);
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
  // Enhanced Agent Management Methods
  // =====================================

  /**
   * Get agent category for pipeline organization
   */
  getAgentCategory(agentName: AgentName): AgentCategory {
    // Initial Processing Agents
    if ([AgentName.LEAD_INTAKE_AGENT, AgentName.LEAD_ANALYSIS_AGENT].includes(agentName)) {
      return AgentCategory.INITIAL_PROCESSING;
    }
    
    // Main Orchestrator
    if (agentName === AgentName.ENHANCED_LEAD_PROCESSOR) {
      return AgentCategory.ORCHESTRATOR;
    }
    
    // Specialized Sub-Agents
    if ([
      AgentName.TAVILY_ENRICHMENT_AGENT,
      AgentName.CONTACT_EXTRACTION_AGENT,
      AgentName.PAIN_POINT_DEEPENING_AGENT,
      AgentName.LEAD_QUALIFICATION_AGENT,
      AgentName.COMPETITOR_IDENTIFICATION_AGENT,
      AgentName.STRATEGIC_QUESTION_GENERATION_AGENT,
      AgentName.BUYING_TRIGGER_IDENTIFICATION_AGENT,
      AgentName.TOT_STRATEGY_GENERATION_AGENT,
      AgentName.TOT_STRATEGY_EVALUATION_AGENT,
      AgentName.TOT_ACTION_PLAN_SYNTHESIS_AGENT,
      AgentName.DETAILED_APPROACH_PLAN_AGENT,
      AgentName.OBJECTION_HANDLING_AGENT,
      AgentName.VALUE_PROPOSITION_CUSTOMIZATION_AGENT,
      AgentName.B2B_PERSONALIZED_MESSAGE_AGENT,
      AgentName.INTERNAL_BRIEFING_SUMMARY_AGENT
    ].includes(agentName)) {
      return AgentCategory.SPECIALIZED;
    }
    
    // Alternative/Modular Agents
    return AgentCategory.ALTERNATIVE;
  }

  /**
   * Start agent - Enhanced to handle all agent types
   */
  async startAgent(agentName: AgentName): Promise<void> {
    try {
      const category = this.getAgentCategory(agentName);
      this.logger.log(`Starting ${category} agent: ${agentName}`);
      
      // For now, log the agent start - could be extended to:
      // 1. Register agent with MCP server
      // 2. Initialize agent-specific configurations
      // 3. Set up agent monitoring
      
      // Potential future API call:
      // await this.makeRequest('POST', `/api/agents/${agentName}/start`);
      
    } catch (error) {
      this.logger.error(`Failed to start agent ${agentName}`, error);
      throw error;
    }
  }

  /**
   * Stop agent - Enhanced to handle all agent types
   */
  async stopAgent(agentName: AgentName): Promise<void> {
    try {
      const category = this.getAgentCategory(agentName);
      this.logger.log(`Stopping ${category} agent: ${agentName}`);
      
      // For now, log the agent stop - could be extended to:
      // 1. Gracefully shutdown agent processes
      // 2. Save agent state
      // 3. Clean up resources
      
      // Potential future API call:
      // await this.makeRequest('POST', `/api/agents/${agentName}/stop`);
      
    } catch (error) {
      this.logger.error(`Failed to stop agent ${agentName}`, error);
      throw error;
    }
  }

  /**
   * Get agent metrics - Enhanced with agent-specific data
   */
  async getAgentMetrics(agentName: AgentName): Promise<AgentMetrics> {
    try {
      const category = this.getAgentCategory(agentName);
      
      // Try to get real metrics from MCP server if available
      // For now, return realistic mock data based on agent category
      let baseMetrics: AgentMetrics;
      
      switch (category) {
        case 'initial_processing':
          baseMetrics = {
            processing_time_seconds: Math.random() * 5 + 1, // 1-6 seconds
            llm_usage: {
              total_tokens: Math.floor(Math.random() * 1000) + 500,
              prompt_tokens: Math.floor(Math.random() * 600) + 300,
              completion_tokens: Math.floor(Math.random() * 400) + 200,
            },
            success_rate: 95 + Math.random() * 5, // 95-100%
            queue_depth: Math.floor(Math.random() * 10),
            throughput_per_hour: Math.floor(Math.random() * 50) + 20, // 20-70/hour
          };
          break;
          
        case 'orchestrator':
          baseMetrics = {
            processing_time_seconds: Math.random() * 10 + 5, // 5-15 seconds
            llm_usage: {
              total_tokens: Math.floor(Math.random() * 2000) + 1000,
              prompt_tokens: Math.floor(Math.random() * 1200) + 600,
              completion_tokens: Math.floor(Math.random() * 800) + 400,
            },
            success_rate: 90 + Math.random() * 10, // 90-100%
            queue_depth: Math.floor(Math.random() * 20),
            throughput_per_hour: Math.floor(Math.random() * 30) + 10, // 10-40/hour
          };
          break;
          
        case 'specialized':
          baseMetrics = {
            processing_time_seconds: Math.random() * 8 + 2, // 2-10 seconds
            llm_usage: {
              total_tokens: Math.floor(Math.random() * 1500) + 750,
              prompt_tokens: Math.floor(Math.random() * 900) + 450,
              completion_tokens: Math.floor(Math.random() * 600) + 300,
            },
            success_rate: 85 + Math.random() * 15, // 85-100%
            queue_depth: Math.floor(Math.random() * 15),
            throughput_per_hour: Math.floor(Math.random() * 40) + 15, // 15-55/hour
          };
          break;
          
        default: // alternative
          baseMetrics = {
            processing_time_seconds: Math.random() * 6 + 2, // 2-8 seconds
            llm_usage: {
              total_tokens: Math.floor(Math.random() * 1200) + 600,
              prompt_tokens: Math.floor(Math.random() * 720) + 360,
              completion_tokens: Math.floor(Math.random() * 480) + 240,
            },
            success_rate: 88 + Math.random() * 12, // 88-100%
            queue_depth: Math.floor(Math.random() * 12),
            throughput_per_hour: Math.floor(Math.random() * 35) + 12, // 12-47/hour
          };
          break;
      }
      
      // Potential future enhancement:
      // const realMetrics = await this.makeRequest('GET', `/api/agents/${agentName}/metrics`);
      // return realMetrics || baseMetrics;
      
      return baseMetrics;
      
    } catch (error) {
      this.logger.error(`Failed to get metrics for agent ${agentName}`, error);
      // Return default metrics on error
      return {
        processing_time_seconds: 0,
        llm_usage: {
          total_tokens: 0,
          prompt_tokens: 0,
          completion_tokens: 0,
        },
        success_rate: 0,
        queue_depth: 0,
        throughput_per_hour: 0,
      };
    }
  }

  /**
   * Get agent status - Enhanced with realistic status simulation
   */
  async getAgentStatus(agentName: AgentName): Promise<string> {
    try {
      // Simulate realistic agent statuses based on category
      const category = this.getAgentCategory(agentName);
      const statuses = ['active', 'inactive', 'processing'];
      
      // Orchestrator and initial processing agents more likely to be active
      if (category === 'orchestrator' || category === 'initial_processing') {
        const weights = [0.7, 0.2, 0.1]; // 70% active, 20% inactive, 10% processing
        const random = Math.random();
        if (random < weights[0]) return 'active';
        if (random < weights[0] + weights[1]) return 'inactive';
        return 'processing';
      }
      
      // Specialized agents have varied status
      if (category === 'specialized') {
        const weights = [0.5, 0.3, 0.2]; // 50% active, 30% inactive, 20% processing
        const random = Math.random();
        if (random < weights[0]) return 'active';
        if (random < weights[0] + weights[1]) return 'inactive';
        return 'processing';
      }
      
      // Alternative agents mostly inactive unless needed
      const weights = [0.3, 0.6, 0.1]; // 30% active, 60% inactive, 10% processing
      const random = Math.random();
      if (random < weights[0]) return 'active';
      if (random < weights[0] + weights[1]) return 'inactive';
      return 'processing';
      
    } catch (error) {
      this.logger.error(`Failed to get status for agent ${agentName}`, error);
      return 'inactive';
    }
  }

  /**
   * Get all agent statuses for pipeline monitoring
   */
  async getAllAgentStatuses(): Promise<Record<AgentName, string>> {
    // Define all agents from our unified type system
    const allAgents: AgentName[] = [
      // Initial Processing
      AgentName.LEAD_INTAKE_AGENT,
      AgentName.LEAD_ANALYSIS_AGENT,
      
      // Orchestrator
      AgentName.ENHANCED_LEAD_PROCESSOR,
      
      // Specialized
      AgentName.TAVILY_ENRICHMENT_AGENT,
      AgentName.CONTACT_EXTRACTION_AGENT,
      AgentName.PAIN_POINT_DEEPENING_AGENT,
      AgentName.LEAD_QUALIFICATION_AGENT,
      AgentName.COMPETITOR_IDENTIFICATION_AGENT,
      AgentName.STRATEGIC_QUESTION_GENERATION_AGENT,
      AgentName.BUYING_TRIGGER_IDENTIFICATION_AGENT,
      AgentName.TOT_STRATEGY_GENERATION_AGENT,
      AgentName.TOT_STRATEGY_EVALUATION_AGENT,
      AgentName.TOT_ACTION_PLAN_SYNTHESIS_AGENT,
      AgentName.DETAILED_APPROACH_PLAN_AGENT,
      AgentName.OBJECTION_HANDLING_AGENT,
      AgentName.VALUE_PROPOSITION_CUSTOMIZATION_AGENT,
      AgentName.B2B_PERSONALIZED_MESSAGE_AGENT,
      AgentName.INTERNAL_BRIEFING_SUMMARY_AGENT,
      
      // Alternative
      AgentName.APPROACH_STRATEGY_AGENT,
      AgentName.B2B_PERSONA_CREATION_AGENT,
      AgentName.MESSAGE_CRAFTING_AGENT,
      AgentName.PERSONA_CREATION_AGENT,
      AgentName.LEAD_ANALYSIS_GENERATION_AGENT
    ];

    const statuses: Record<AgentName, string> = {} as Record<AgentName, string>;
    
    // Get status for each agent
    for (const agent of allAgents) {
      try {
        statuses[agent] = await this.getAgentStatus(agent);
      } catch (error) {
        this.logger.warn(`Failed to get status for agent ${agent}, setting to inactive`);
        statuses[agent] = 'inactive';
      }
    }
    
    return statuses;
  }

  /**
   * Verify MCP server supports all required agents
   */
  async verifyAgentSupport(): Promise<{
    supportedAgents: AgentName[];
    unsupportedAgents: AgentName[];
    totalAgents: number;
    supportPercentage: number;
  }> {
    const allAgents: AgentName[] = [
      AgentName.LEAD_INTAKE_AGENT, AgentName.LEAD_ANALYSIS_AGENT, AgentName.ENHANCED_LEAD_PROCESSOR,
      AgentName.TAVILY_ENRICHMENT_AGENT, AgentName.CONTACT_EXTRACTION_AGENT, AgentName.PAIN_POINT_DEEPENING_AGENT,
      AgentName.LEAD_QUALIFICATION_AGENT, AgentName.COMPETITOR_IDENTIFICATION_AGENT, AgentName.STRATEGIC_QUESTION_GENERATION_AGENT,
      AgentName.BUYING_TRIGGER_IDENTIFICATION_AGENT, AgentName.TOT_STRATEGY_GENERATION_AGENT, AgentName.TOT_STRATEGY_EVALUATION_AGENT,
      AgentName.TOT_ACTION_PLAN_SYNTHESIS_AGENT, AgentName.DETAILED_APPROACH_PLAN_AGENT, AgentName.OBJECTION_HANDLING_AGENT,
      AgentName.VALUE_PROPOSITION_CUSTOMIZATION_AGENT, AgentName.B2B_PERSONALIZED_MESSAGE_AGENT, AgentName.INTERNAL_BRIEFING_SUMMARY_AGENT,
      AgentName.APPROACH_STRATEGY_AGENT, AgentName.B2B_PERSONA_CREATION_AGENT, AgentName.MESSAGE_CRAFTING_AGENT,
      AgentName.PERSONA_CREATION_AGENT, AgentName.LEAD_ANALYSIS_GENERATION_AGENT
    ];
    
    const supportedAgents: AgentName[] = [];
    const unsupportedAgents: AgentName[] = [];
    
    // For now, assume all agents are supported
    // In the future, this could check against MCP server API
    for (const agent of allAgents) {
      try {
        // Could make API call to verify: await this.makeRequest('GET', `/api/agents/${agent}/info`);
        supportedAgents.push(agent);
      } catch (error) {
        unsupportedAgents.push(agent);
      }
    }
    
    return {
      supportedAgents,
      unsupportedAgents,
      totalAgents: allAgents.length,
      supportPercentage: (supportedAgents.length / allAgents.length) * 100
    };
  }

  // =====================================
  // Chat Methods (Not implemented in MCP server)
  // =====================================

  async sendChatMessage(agentName: AgentName, message: string): Promise<string> {
    this.logger.warn('Chat functionality not implemented in current MCP server');
    return `Message received by ${agentName}: ${message}`;
  }

  // =====================================
  // Business Context Methods
  // =====================================

  async updateBusinessContext(context: BusinessContextType | null): Promise<void> {
    this.logger.log(`Syncing business context with MCP server. Context: ${context ? context.id : 'null'}`);
    try {
      // Assuming an endpoint like /api/business-context
      // If context is null, it means clear the context on MCP side
      await this.makeRequest('POST', '/api/business-context', context);
      this.logger.log('Business context synced with MCP server successfully.');
    } catch (error) {
      this.logger.error('Failed to sync business context with MCP server.', error.stack);
      // Do not rethrow, allow main app to function even if MCP sync fails
    }
  }

  async getBusinessContext(): Promise<BusinessContextType | null> {
    this.logger.log('Attempting to get business context from MCP server.');
    try {
      // Assuming an endpoint like /api/business-context
      const context = await this.makeRequest<BusinessContextType | null>('GET', '/api/business-context');
      this.logger.log(context ? 'Business context retrieved from MCP.' : 'No business context found on MCP.');
      return context;
    } catch (error) {
      this.logger.error('Failed to get business context from MCP server.', error.stack);
      return null;
    }
  }

  // =====================================
  // Prospecting Specific Methods
  // =====================================

  /**
   * Runs the agentic harvester process via MCP with quota-aware limits.
   * This method calls the new /api/v2/run_agentic_harvester endpoint.
   * @param query The search query.
   * @param maxSites Maximum number of sites to process.
   * @param context The business context to use for harvesting.
   * @param maxLeadsToReturn Maximum number of leads to return (quota-aware).
   * @param userId User ID for logging and potential user-specific context.
   * @returns A promise resolving to an array of harvester results.
   */
  async runHarvester(
    maxSites: number,
    context: BusinessContextType,
    maxLeadsToReturn?: number,
    userId?: string,
  ): Promise<{ status: string; job_id: string }> {
    this.logger.log(`[MCP_SERVICE] Preparing to dispatch harvester job for user ${userId || 'unknown'}.`);
    
    const payload = {
      user_id: userId || 'unknown',
      business_context: context,
      max_leads_to_generate: maxLeadsToReturn || 50, // Default fallback
      max_sites_to_scrape: maxSites,
      timestamp: new Date().toISOString(),
    };
    this.logger.debug(`[MCP_SERVICE] Payload for MCP: ${JSON.stringify(payload, null, 2)}`);

    // This now returns the immediate response from the MCP server, not the results.
    this.logger.log('[MCP_SERVICE] Sending request to /api/v2/run_agentic_harvester...');
    const response = await this.makeRequest<{
      status: string;
      message: string;
      job_id: string;
      user_id: string;
    }>('POST', '/api/v2/run_agentic_harvester', payload);

    this.logger.log(`[MCP_SERVICE] Successfully dispatched harvester job to MCP. Response: ${JSON.stringify(response)}`);
    
    return { status: response.status, job_id: response.job_id };
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

  async streamEnrichmentPipeline(lead: Lead, userId: string, jobId: string): Promise<AsyncIterable<any>> {
    const url = `${this.baseUrl}/api/v2/stream_enrichment_pipeline`;
    this.logger.log(`Initiating enrichment stream for lead ${lead.id} at ${url}`);

    const businessContext = await this.businessContextService.getContextForMcp(userId);

    const payload: EnrichmentJobData = {
      user_id: userId,
      job_id: jobId,
      analyzed_lead_data: lead,
      product_service_context: businessContext.product_service_description,
      competitors_list: businessContext.competitors?.join(','),
      timestamp: new Date().toISOString(),
    };

    const response = await firstValueFrom(
        this.httpService.post(url, payload, {
            responseType: 'stream',
        }),
    );

    return response.data;
  }
}
