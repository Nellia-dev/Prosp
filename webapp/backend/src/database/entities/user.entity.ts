import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
  Index,
  OneToMany,
} from 'typeorm';
import { Exclude } from 'class-transformer';
import { PlanId, DEFAULT_PLAN } from '../../config/plans.config';
import { Lead } from './lead.entity';

export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
}

@Entity('users')
@Index(['email'], { unique: true })
export class User {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ type: 'varchar', length: 255, unique: true })
  email: string;

  @Column({ type: 'varchar', length: 255 })
  @Exclude()
  password: string;

  @Column({ type: 'varchar', length: 100 })
  first_name: string;

  @Column({ type: 'varchar', length: 100 })
  last_name: string;

  @Column({
    type: 'enum',
    enum: UserRole,
    default: UserRole.USER,
  })
  role: UserRole;

  @Column({ type: 'boolean', default: true })
  is_active: boolean;

  @Column({ type: 'timestamp', nullable: true })
  last_login: Date;

  // Plan and quota tracking fields
  @Column({
    type: 'enum',
    enum: ['free', 'starter', 'pro', 'enterprise'],
    default: DEFAULT_PLAN,
  })
  plan: PlanId;

  @Column({ type: 'integer', default: 0 })
  currentLeadQuotaUsed: number;

  @Column({ type: 'timestamp', nullable: true })
  lastQuotaResetAt: Date;

  @Column({ type: 'varchar', nullable: true, unique: true })
  prospectingJobId: string;

  // Prospect cooldown tracking fields
  @Column({ type: 'timestamp', nullable: true })
  lastProspectCompletedAt: Date;

  @Column({ type: 'timestamp', nullable: true })
  prospectCooldownUntil: Date;

  // Relations
  @OneToMany(() => Lead, (lead) => lead.user)
  leads: Lead[];

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;

  // Virtual property to get full name
  get fullName(): string {
    return `${this.first_name} ${this.last_name}`;
  }
}
