import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('business_context')
export class BusinessContextEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'text' })
  business_description: string;

  @Column({ type: 'text' })
  target_market: string;

  @Column({ type: 'text' })
  value_proposition: string;

  @Column({ type: 'text' })
  ideal_customer: string;

  @Column({ type: 'text', array: true, default: [] })
  pain_points: string[];

  @Column({ type: 'text' })
  competitive_advantage: string;

  @Column({ type: 'text', array: true, default: [] })
  industry_focus: string[];

  @Column({ type: 'text', array: true, default: ['Brasil'] })
  geographic_focus: string[];

  @Column({ type: 'boolean', default: true })
  is_active: boolean;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;
}
