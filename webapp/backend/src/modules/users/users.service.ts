import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from '../../database/entities/user.entity';
import { PlanId } from '../../config/plans.config';

@Injectable()
export class UsersService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
  ) {}

  /**
   * Get user by ID with plan details
   */
  async getUserById(userId: string): Promise<User> {
    const user = await this.userRepository.findOne({
      where: { id: userId },
      relations: ['leads'], // Include leads if needed
    });

    if (!user) {
      throw new NotFoundException(`User with ID ${userId} not found`);
    }

    return user;
  }

  /**
   * Update user's subscription plan
   */
  async updateUserPlan(userId: string, newPlanId: PlanId): Promise<User> {
    const user = await this.getUserById(userId);
    
    user.plan = newPlanId;
    // Reset quota when plan changes
    user.currentLeadQuotaUsed = 0;
    user.lastQuotaResetAt = new Date();
    
    return await this.userRepository.save(user);
  }

  /**
   * Record that a prospecting job has started for this user
   */
  async recordProspectingJobStart(userId: string, jobId: string): Promise<User> {
    const user = await this.getUserById(userId);
    
    user.prospectingJobId = jobId;
    
    return await this.userRepository.save(user);
  }

  /**
   * Clear the prospecting job ID when job completes and set cooldown for non-enterprise plans
   */
  async clearProspectingJob(userId: string): Promise<User> {
    const user = await this.getUserById(userId);
    
    user.prospectingJobId = null;
    user.lastProspectCompletedAt = new Date();
    
    // Set 24-hour cooldown for non-enterprise plans
    if (user.plan !== 'enterprise') {
      const cooldownUntil = new Date();
      cooldownUntil.setHours(cooldownUntil.getHours() + 24);
      user.prospectCooldownUntil = cooldownUntil;
    }
    
    return await this.userRepository.save(user);
  }

  /**
   * Check if user is in prospect cooldown period
   */
  async isInProspectCooldown(userId: string): Promise<boolean> {
    const user = await this.getUserById(userId);
    
    // Enterprise users don't have cooldown
    if (user.plan === 'enterprise') {
      return false;
    }
    
    // Check if cooldown period has passed
    if (user.prospectCooldownUntil) {
      return new Date() < user.prospectCooldownUntil;
    }
    
    return false;
  }

  /**
   * Get remaining cooldown time in milliseconds
   */
  async getRemainingCooldownTime(userId: string): Promise<number> {
    const user = await this.getUserById(userId);
    
    // Enterprise users don't have cooldown
    if (user.plan === 'enterprise') {
      return 0;
    }
    
    if (user.prospectCooldownUntil) {
      const remaining = user.prospectCooldownUntil.getTime() - new Date().getTime();
      return Math.max(0, remaining);
    }
    
    return 0;
  }

  /**
   * Clear prospect cooldown (for testing or admin purposes)
   */
  async clearProspectCooldown(userId: string): Promise<User> {
    const user = await this.getUserById(userId);
    
    user.prospectCooldownUntil = null;
    
    return await this.userRepository.save(user);
  }

  /**
   * Find user by email (for authentication)
   */
  async findByEmail(email: string): Promise<User | null> {
    return await this.userRepository.findOne({
      where: { email },
    });
  }

  /**
   * Create a new user
   */
  async create(userData: Partial<User>): Promise<User> {
    const user = this.userRepository.create({
      ...userData,
      plan: 'free', // Default plan
      currentLeadQuotaUsed: 0,
      lastQuotaResetAt: new Date(),
    });

    return await this.userRepository.save(user);
  }
}
