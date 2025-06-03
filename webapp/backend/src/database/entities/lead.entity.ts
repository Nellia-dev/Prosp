import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';
import { ProcessingStage, QualificationTier } from '../../shared/types/nellia.types';

@Entity('leads')
export class Lead {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  company_name: string;

  @Column()
  website: string;

  @Column({ type: 'decimal', precision: 3, scale: 2 })
  relevance_score: number;

  @Column({ type: 'decimal', precision: 3, scale: 2 })
  roi_potential_score: number;

  @Column({ type: 'decimal', precision: 3, scale: 2 })
  brazilian_market_fit: number;

  @Column({
    type: 'enum',
    enum: ['High Potential', 'Medium Potential', 'Low Potential'],
  })
  qualification_tier: QualificationTier;

  @Column()
  company_sector: string;

  @Column({ type: 'jsonb', nullable: true })
  persona: {
    likely_role: string;
    decision_maker_probability: number;
  };

  @Column({ type: 'text', array: true, nullable: true })
  pain_point_analysis: string[];

  @Column({ type: 'text', array: true, nullable: true })
  purchase_triggers: string[];

  @Column({
    type: 'enum',
    enum: ['intake', 'analysis', 'persona', 'strategy', 'message', 'completed'],
    default: 'intake',
  })
  processing_stage: ProcessingStage;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;
}
