import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';
import { AgentMetrics } from '../../shared/types/nellia.types';
import { AgentName, AgentStatus, AgentCategory } from '../../shared/enums/nellia.enums';

@Entity('agents')
export class Agent {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    type: 'enum',
    enum: AgentName,
    nullable: false,
  })
  name: AgentName;

  @Column({
    type: 'enum',
    enum: AgentStatus,
    default: AgentStatus.INACTIVE,
  })
  status: AgentStatus;

  @Column({ type: 'jsonb', nullable: false })
  metrics: AgentMetrics;

  @Column({ type: 'varchar', nullable: true })
  currentTask: string | null;

  @Column({ type: 'text', nullable: true })
  description: string;

  @Column({
    type: 'enum',
    enum: AgentCategory,
    nullable: true,
  })
  category: AgentCategory;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;

  @Column({ type: 'timestamp', default: () => 'CURRENT_TIMESTAMP' })
  last_updated: Date;

  // Additional computed fields for backward compatibility and extended functionality
  @Column({ type: 'int', default: 0 })
  throughput: number;

  @Column({ type: 'int', default: 0 })
  llmTokenUsage: number;

  @Column({ type: 'decimal', precision: 5, scale: 2, default: 0 })
  successRate: number;

  @Column({ type: 'int', default: 0 })
  queueDepth: number;

  @Column({ type: 'decimal', precision: 8, scale: 2, default: 0 })
  processingTime: number;

  // Helper method to get agent category
  getCategory(): 'initial_processing' | 'orchestrator' | 'specialized' | 'alternative' {
    if ([AgentName.LEAD_INTAKE_AGENT, AgentName.LEAD_ANALYSIS_AGENT].includes(this.name)) {
      return 'initial_processing';
    }
    if (this.name === AgentName.ENHANCED_LEAD_PROCESSOR) {
      return 'orchestrator';
    }
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
      AgentName.INTERNAL_BRIEFING_SUMMARY_AGENT,
    ].includes(this.name)) {
      return 'specialized';
    }
    return 'alternative';
  }

  // Helper method to get display name
  getDisplayName(): string {
    const displayNames: Record<AgentName, string> = {
      // Initial Processing Agents
      [AgentName.LEAD_INTAKE_AGENT]: 'Lead Intake Agent',
      [AgentName.LEAD_ANALYSIS_AGENT]: 'Lead Analysis Agent',
      
      // Main Orchestrator
      [AgentName.ENHANCED_LEAD_PROCESSOR]: 'Enhanced Lead Processor',
      
      // Specialized Sub-Agents
      [AgentName.TAVILY_ENRICHMENT_AGENT]: 'Web Research Agent',
      [AgentName.CONTACT_EXTRACTION_AGENT]: 'Contact Extraction Agent',
      [AgentName.PAIN_POINT_DEEPENING_AGENT]: 'Pain Point Analysis Agent',
      [AgentName.LEAD_QUALIFICATION_AGENT]: 'Lead Qualification Agent',
      [AgentName.COMPETITOR_IDENTIFICATION_AGENT]: 'Competitor Analysis Agent',
      [AgentName.STRATEGIC_QUESTION_GENERATION_AGENT]: 'Strategic Questions Agent',
      [AgentName.BUYING_TRIGGER_IDENTIFICATION_AGENT]: 'Buying Triggers Agent',
      [AgentName.TOT_STRATEGY_GENERATION_AGENT]: 'Strategy Generation Agent',
      [AgentName.TOT_STRATEGY_EVALUATION_AGENT]: 'Strategy Evaluation Agent',
      [AgentName.TOT_ACTION_PLAN_SYNTHESIS_AGENT]: 'Action Plan Synthesis Agent',
      [AgentName.DETAILED_APPROACH_PLAN_AGENT]: 'Approach Planning Agent',
      [AgentName.OBJECTION_HANDLING_AGENT]: 'Objection Handling Agent',
      [AgentName.VALUE_PROPOSITION_CUSTOMIZATION_AGENT]: 'Value Proposition Agent',
      [AgentName.B2B_PERSONALIZED_MESSAGE_AGENT]: 'Message Personalization Agent',
      [AgentName.INTERNAL_BRIEFING_SUMMARY_AGENT]: 'Internal Briefing Agent',
      
      // Alternative/Modular Agents
      [AgentName.APPROACH_STRATEGY_AGENT]: 'Approach Strategy Agent',
      [AgentName.B2B_PERSONA_CREATION_AGENT]: 'B2B Persona Agent',
      [AgentName.MESSAGE_CRAFTING_AGENT]: 'Message Crafting Agent',
      [AgentName.PERSONA_CREATION_AGENT]: 'Persona Creation Agent',
      [AgentName.LEAD_ANALYSIS_GENERATION_AGENT]: 'Analysis Generation Agent',
    };

    return displayNames[this.name] || this.name;
  }

  // Method to sync computed fields with metrics for API compatibility
  syncMetricsToFields(): void {
    if (this.metrics) {
      this.throughput = Math.round(this.metrics.throughput_per_hour);
      this.llmTokenUsage = this.metrics.llm_usage?.total_tokens || 0;
      this.successRate = this.metrics.success_rate;
      this.queueDepth = this.metrics.queue_depth;
      this.processingTime = this.metrics.processing_time_seconds;
    }
  }

  // Method to update metrics from computed fields
  syncFieldsToMetrics(): void {
    if (!this.metrics) {
      this.metrics = {
        processing_time_seconds: 0,
        llm_usage: { total_tokens: 0, prompt_tokens: 0, completion_tokens: 0 },
        success_rate: 0,
        queue_depth: 0,
        throughput_per_hour: 0,
      };
    }
    
    this.metrics.throughput_per_hour = this.throughput || 0;
    this.metrics.success_rate = this.successRate || 0;
    this.metrics.queue_depth = this.queueDepth || 0;
    this.metrics.processing_time_seconds = this.processingTime || 0;
    
    if (this.llmTokenUsage) {
      this.metrics.llm_usage.total_tokens = this.llmTokenUsage;
    }
  }
}

// Re-export the enums for backward compatibility
export { AgentName, AgentStatus } from '../../shared/enums/nellia.enums';
