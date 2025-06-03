import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Agent } from '../../database/entities/agent.entity';
import { AgentStatus, AgentMetrics, AgentName } from '../../shared/types/nellia.types';
import { McpService } from '../mcp/mcp.service';

@Injectable()
export class AgentsService {
  constructor(
    @InjectRepository(Agent)
    private readonly agentRepository: Repository<Agent>,
    private readonly mcpService: McpService,
  ) {}

  async findAll(): Promise<AgentStatus[]> {
    const agents = await this.agentRepository.find({
      order: { created_at: 'ASC' },
    });

    return agents.map(this.mapToAgentStatus);
  }

  async findOne(id: string): Promise<AgentStatus> {
    const agent = await this.agentRepository.findOne({ where: { id } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with ID ${id} not found`);
    }

    return this.mapToAgentStatus(agent);
  }

  async findByName(name: AgentName): Promise<AgentStatus> {
    const agent = await this.agentRepository.findOne({ where: { name } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with name ${name} not found`);
    }

    return this.mapToAgentStatus(agent);
  }

  async updateAgentStatus(id: string, status: 'active' | 'inactive' | 'processing' | 'error' | 'completed'): Promise<AgentStatus> {
    const agent = await this.agentRepository.findOne({ where: { id } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with ID ${id} not found`);
    }

    agent.status = status;
    agent.last_updated = new Date();
    
    const updatedAgent = await this.agentRepository.save(agent);
    return this.mapToAgentStatus(updatedAgent);
  }

  async updateAgentMetrics(id: string, metrics: AgentMetrics): Promise<AgentStatus> {
    const agent = await this.agentRepository.findOne({ where: { id } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with ID ${id} not found`);
    }

    agent.metrics = metrics;
    agent.last_updated = new Date();
    
    const updatedAgent = await this.agentRepository.save(agent);
    return this.mapToAgentStatus(updatedAgent);
  }

  async updateCurrentTask(id: string, task: string): Promise<AgentStatus> {
    const agent = await this.agentRepository.findOne({ where: { id } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with ID ${id} not found`);
    }

    agent.current_task = task;
    agent.last_updated = new Date();
    
    const updatedAgent = await this.agentRepository.save(agent);
    return this.mapToAgentStatus(updatedAgent);
  }

  async startAgent(id: string): Promise<AgentStatus> {
    const agent = await this.agentRepository.findOne({ where: { id } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with ID ${id} not found`);
    }

    // Communicate with MCP server to start the agent
    try {
      await this.mcpService.startAgent(agent.name);
      
      agent.status = 'active';
      agent.last_updated = new Date();
      
      const updatedAgent = await this.agentRepository.save(agent);
      return this.mapToAgentStatus(updatedAgent);
    } catch (error) {
      agent.status = 'error';
      agent.last_updated = new Date();
      await this.agentRepository.save(agent);
      throw error;
    }
  }

  async stopAgent(id: string): Promise<AgentStatus> {
    const agent = await this.agentRepository.findOne({ where: { id } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with ID ${id} not found`);
    }

    // Communicate with MCP server to stop the agent
    try {
      await this.mcpService.stopAgent(agent.name);
      
      agent.status = 'inactive';
      agent.current_task = null;
      agent.last_updated = new Date();
      
      const updatedAgent = await this.agentRepository.save(agent);
      return this.mapToAgentStatus(updatedAgent);
    } catch (error) {
      agent.status = 'error';
      agent.last_updated = new Date();
      await this.agentRepository.save(agent);
      throw error;
    }
  }

  async getAgentMetrics(id: string): Promise<AgentMetrics> {
    const agent = await this.agentRepository.findOne({ where: { id } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with ID ${id} not found`);
    }

    // Get real-time metrics from MCP server
    try {
      const metrics = await this.mcpService.getAgentMetrics(agent.name);
      
      // Update stored metrics
      agent.metrics = metrics;
      agent.last_updated = new Date();
      await this.agentRepository.save(agent);
      
      return metrics;
    } catch (error) {
      // Fallback to stored metrics
      return agent.metrics;
    }
  }

  async initializeDefaultAgents(): Promise<void> {
    const agentNames: AgentName[] = [
      'lead_intake',
      'analysis',
      'persona_creation',
      'approach_strategy',
      'message_crafting',
    ];

    const defaultMetrics: AgentMetrics = {
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

    for (const name of agentNames) {
      const existingAgent = await this.agentRepository.findOne({ where: { name } });
      
      if (!existingAgent) {
        const agent = this.agentRepository.create({
          name,
          status: 'inactive',
          metrics: defaultMetrics,
        });
        
        await this.agentRepository.save(agent);
      }
    }
  }

  private mapToAgentStatus(agent: Agent): AgentStatus {
    return {
      id: agent.id,
      name: agent.name,
      status: agent.status,
      metrics: agent.metrics,
      last_updated: agent.last_updated.toISOString(),
      current_task: agent.current_task,
    };
  }
}
