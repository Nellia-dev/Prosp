import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn, ManyToOne, JoinColumn } from 'typeorm';
import { ProcessingStage, QualificationTier, LeadStatus } from '../../shared/enums/nellia.enums';
import { User } from './user.entity';

@Entity('leads')
export class Lead {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  // User relationship - lead ownership
  @Column({ type: 'uuid' })
  userId: string;

  @ManyToOne(() => User, (user) => user.leads, { nullable: false })
  @JoinColumn({ name: 'userId' })
  user: User;

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
    enum: QualificationTier,
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
    enum: ProcessingStage,
    default: ProcessingStage.INTAKE,
  })
  processing_stage: ProcessingStage;

  @Column({
    type: 'enum',
    enum: LeadStatus,
    default: LeadStatus.NEW,
  })
  status: LeadStatus;

  @Column({ type: 'jsonb', nullable: true })
  enrichment_data: any;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;

    // Additional optional fields for extended lead data
  @Column({ type: 'varchar', nullable: true })
  description?: string;

  @Column({ type: 'varchar', nullable: true })
  contact_email?: string;

  @Column({ type: 'varchar', nullable: true })
  contact_phone?: string;

  @Column({ type: 'varchar', nullable: true })
  contact_role?: string;

  @Column({ type: 'varchar', nullable: true })
  market_region?: string;

  @Column({ type: 'varchar', nullable: true })
  company_size?: string;

  @Column({ type: 'decimal', precision: 15, scale: 2, nullable: true })
  annual_revenue?: number;

  @Column({ type: 'text', nullable: true })
  persona_analysis?: string;

  @Column({ type: 'decimal', precision: 3, scale: 2, nullable: true })
  decision_maker_probability?: number;

    get stage(): string {
      return this.processing_stage;
    }
  
    set stage(value: string) {
      this.processing_stage = value as ProcessingStage;
    }
}
