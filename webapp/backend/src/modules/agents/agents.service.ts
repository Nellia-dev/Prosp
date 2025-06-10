import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Agent, AgentName, AgentStatus as AgentStatusEnum } from '../../database/entities/agent.entity';
import { AgentStatus, AgentMetrics, AgentCategory } from '../../shared/types/nellia.types';

@Injectable()
export class AgentsService {
  constructor(
    @InjectRepository(Agent)
    private readonly agentRepository: Repository<Agent>,
  ) {}

  async findAll(): Promise<AgentStatus[]> {
    try {
      const agents = await this.agentRepository.find({
        order: { name: 'ASC' },
      });
      
      return agents.map(agent => this.convertToAgentStatus(agent));
    } catch (error) {
      console.error('Error fetching agents:', error);
      return []; // Always return empty array, never undefined
    }
  }

  async findOne(id: string): Promise<AgentStatus> {
    const agent = await this.agentRepository.findOne({ where: { id } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with ID ${id} not found`);
    }
    
    return this.convertToAgentStatus(agent);
  }

  async findByName(name: AgentName): Promise<Agent | null> {
    const agent = await this.agentRepository.findOne({ where: { name } });
    
    if (agent) {
      agent.syncMetricsToFields();
    }
    
    return agent;
  }

  async findByCategory(category: AgentCategory): Promise<AgentStatus[]> {
    const agents = await this.agentRepository.find({
      order: { name: 'ASC' },
    });
    
    const filteredAgents = agents.filter(agent => agent.getCategory() === category);
    return filteredAgents.map(agent => this.convertToAgentStatus(agent));
  }

  async findByStatus(status: AgentStatusEnum): Promise<Agent[]> {
    const agents = await this.agentRepository.find({ 
      where: { status },
      order: { name: 'ASC' },
    });
    
    agents.forEach(agent => agent.syncMetricsToFields());
    return agents;
  }

  async startAgent(id: string): Promise<AgentStatus> {
    const agent = await this.getAgentEntity(id);
    
    agent.status = AgentStatusEnum.ACTIVE;
    agent.currentTask = null;
    agent.last_updated = new Date();
    
    await this.agentRepository.save(agent);
    return this.convertToAgentStatus(agent);
  }

  async stopAgent(id: string): Promise<AgentStatus> {
    const agent = await this.getAgentEntity(id);
    
    agent.status = AgentStatusEnum.INACTIVE;
    agent.currentTask = null;
    agent.last_updated = new Date();
    
    await this.agentRepository.save(agent);
    return this.convertToAgentStatus(agent);
  }

  async getAgentMetrics(id: string): Promise<AgentMetrics> {
    const agent = await this.getAgentEntity(id);
    agent.syncMetricsToFields();
    return agent.metrics;
  }

  async getAgentsByPipeline(): Promise<{
    initial: AgentStatus[];
    orchestrator: AgentStatus[];
    specialized: AgentStatus[];
    alternative: AgentStatus[];
  }> {
    const agents = await this.findAll();
    
    return {
      initial: agents.filter(agent => agent.category === 'initial_processing'),
      orchestrator: agents.filter(agent => agent.category === 'orchestrator'),
      specialized: agents.filter(agent => agent.category === 'specialized'),
      alternative: agents.filter(agent => agent.category === 'alternative'),
    };
  }

  async getAllAgentsByCategory(): Promise<Record<AgentCategory, AgentStatus[]>> {
    const agents = await this.findAll();
    
    return {
      initial_processing: agents.filter(agent => agent.category === 'initial_processing'),
      orchestrator: agents.filter(agent => agent.category === 'orchestrator'),
      specialized: agents.filter(agent => agent.category === 'specialized'),
      alternative: agents.filter(agent => agent.category === 'alternative'),
    };
  }

  // Method for updating agent metrics (used by metrics collector)
  async updateAgentMetrics(id: string, metrics: Partial<AgentMetrics>): Promise<Agent> {
    return this.updateMetrics(id, metrics);
  }

  async updateStatus(id: string, status: AgentStatusEnum, currentTask?: string): Promise<Agent> {
    const agent = await this.getAgentEntity(id);
    
    agent.status = status;
    agent.currentTask = currentTask || null;
    agent.last_updated = new Date();
    
    return this.agentRepository.save(agent);
  }

  async updateMetrics(id: string, metrics: Partial<AgentMetrics>): Promise<Agent> {
    const agent = await this.getAgentEntity(id);
    
    agent.metrics = { ...agent.metrics, ...metrics };
    agent.syncMetricsToFields();
    
    return this.agentRepository.save(agent);
  }

  async incrementThroughput(id: string): Promise<Agent> {
    const agent = await this.getAgentEntity(id);
    
    agent.throughput += 1;
    agent.syncFieldsToMetrics();
    
    return this.agentRepository.save(agent);
  }

  async addTokenUsage(id: string, tokens: number): Promise<Agent> {
    const agent = await this.getAgentEntity(id);
    
    agent.llmTokenUsage += tokens;
    if (agent.metrics.llm_usage) {
      agent.metrics.llm_usage.total_tokens += tokens;
    }
    
    return this.agentRepository.save(agent);
  }

  async updateSuccessRate(id: string, successRate: number): Promise<Agent> {
    const agent = await this.getAgentEntity(id);
    
    agent.successRate = successRate;
    agent.syncFieldsToMetrics();
    
    return this.agentRepository.save(agent);
  }

  async getActiveAgentsCount(): Promise<number> {
    return this.agentRepository.count({ where: { status: AgentStatusEnum.ACTIVE } });
  }

  async getProcessingAgentsCount(): Promise<number> {
    return this.agentRepository.count({ where: { status: AgentStatusEnum.PROCESSING } });
  }

  async getAgentStats(): Promise<{
    total: number;
    active: number;
    inactive: number;
    processing: number;
    error: number;
  }> {
    const [total, active, inactive, processing, error] = await Promise.all([
      this.agentRepository.count(),
      this.agentRepository.count({ where: { status: AgentStatusEnum.ACTIVE } }),
      this.agentRepository.count({ where: { status: AgentStatusEnum.INACTIVE } }),
      this.agentRepository.count({ where: { status: AgentStatusEnum.PROCESSING } }),
      this.agentRepository.count({ where: { status: AgentStatusEnum.ERROR } }),
    ]);

    return { total, active, inactive, processing, error };
  }

  async getTotalThroughput(): Promise<number> {
    const result = await this.agentRepository
      .createQueryBuilder('agent')
      .select('SUM(agent.throughput)', 'total')
      .getRawOne();
    
    return parseInt(result.total) || 0;
  }

  async getTotalTokenUsage(): Promise<number> {
    const result = await this.agentRepository
      .createQueryBuilder('agent')
      .select('SUM(agent.llmTokenUsage)', 'total')
      .getRawOne();
    
    return parseInt(result.total) || 0;
  }

  async getAverageProcessingTime(): Promise<number> {
    const result = await this.agentRepository
      .createQueryBuilder('agent')
      .select('AVG(agent.processingTime)', 'average')
      .getRawOne();
    
    return parseFloat(result.average) || 0;
  }

  // Helper method to get agent entity
  private async getAgentEntity(id: string): Promise<Agent> {
    const agent = await this.agentRepository.findOne({ where: { id } });
    
    if (!agent) {
      throw new NotFoundException(`Agent with ID ${id} not found`);
    }
    
    agent.syncMetricsToFields();
    return agent;
  }

  // Convert Agent entity to AgentStatus for API responses
  private convertToAgentStatus(agent: Agent): AgentStatus {
    agent.syncMetricsToFields();
    
    return {
      id: agent.id,
      name: agent.name,
      status: agent.status as any,
      metrics: agent.metrics,
      last_updated: agent.last_updated.toISOString(),
      current_task: agent.currentTask,
      description: `${agent.getDisplayName()} - ${agent.getCategory()} agent`,
      category: agent.getCategory() as AgentCategory,
    };
  }
}
