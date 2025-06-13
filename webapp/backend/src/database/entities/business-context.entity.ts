import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn, ManyToOne, JoinColumn, Index } from 'typeorm';
import { User } from './user.entity';

@Entity('business_context')
export class BusinessContextEntity {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Index()
  @Column({ type: 'uuid' })
  userId: string;

  @ManyToOne(() => User, { nullable: false })
  @JoinColumn({ name: 'userId' })
  user: User;

  @Column({ type: 'text' })
  business_description: string;

  @Column({ type: 'text' })
  product_service_description: string;

  @Column({ type: 'text' })
  target_market: string;

  @Column({ type: 'text' })
  value_proposition: string;

  @Column({ type: 'text', nullable: true })
  ideal_customer: string;

  @Column({ type: 'text', array: true, default: [] })
  pain_points: string[];

  @Column({ type: 'text', nullable: true })
  competitive_advantage: string;

  @Column({ type: 'text', array: true, default: [] })
  competitors: string[];

  @Column({ type: 'text', array: true, default: [] })
  industry_focus: string[];

  @Column({ type: 'text', array: true, default: ['Brasil'] })
  geographic_focus: string[];

  @Column({ type: 'text', nullable: true })
  search_query: string;

  @Column({ type: 'boolean', default: true })
  is_active: boolean;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;
}
