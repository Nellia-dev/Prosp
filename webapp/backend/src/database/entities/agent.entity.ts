import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';
import { AgentMetrics, AgentName } from '../../shared/types/nellia.types';

@Entity('agents')
export class Agent {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({
    type: 'enum',
    enum: ['lead_intake', 'analysis', 'persona_creation', 'approach_strategy', 'message_crafting'],
  })
  name: AgentName;

  @Column({
    type: 'enum',
    enum: ['active', 'inactive', 'processing', 'error', 'completed'],
    default: 'inactive',
  })
  status: 'active' | 'inactive' | 'processing' | 'error' | 'completed';

  @Column({ type: 'jsonb' })
  metrics: AgentMetrics;

  @Column({ nullable: true })
  current_task: string;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;

  @Column({ type: 'timestamp', default: () => 'CURRENT_TIMESTAMP' })
  last_updated: Date;
}
