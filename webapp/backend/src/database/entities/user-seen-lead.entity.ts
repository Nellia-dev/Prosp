import { Entity, PrimaryColumn, CreateDateColumn, ManyToOne, JoinColumn } from 'typeorm';
import { User } from './user.entity';
import { Lead } from './lead.entity';

@Entity('user_seen_leads')
export class UserSeenLead {
  @PrimaryColumn('uuid')
  userId: string;

  @PrimaryColumn('uuid')
  leadId: string;

  @ManyToOne(() => User, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'userId' })
  user: User;

  @ManyToOne(() => Lead, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'leadId' })
  lead: Lead;

  @CreateDateColumn({ type: 'timestamp with time zone' })
  seenAt: Date;
}
