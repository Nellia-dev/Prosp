import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, ManyToOne, JoinColumn } from 'typeorm';
import { Agent } from './agent.entity';

@Entity('chat_messages')
export class ChatMessage {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  agent_id: string;

  @ManyToOne(() => Agent)
  @JoinColumn({ name: 'agent_id' })
  agent: Agent;

  @Column({ type: 'text' })
  content: string;

  @Column({
    type: 'enum',
    enum: ['user', 'agent'],
  })
  type: 'user' | 'agent';

  @Column({ type: 'text', array: true, nullable: true })
  attachments: string[];

  @CreateDateColumn()
  timestamp: Date;

  @CreateDateColumn()
  created_at: Date;
}
