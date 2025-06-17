import { Injectable, Logger } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from '../../database/entities/user.entity';
import { PlanId, PlanDetails, PLANS } from '../../config/plans.config';

@Injectable()
export class QuotaService {
  private readonly logger = new Logger(QuotaService.name);
  
  // Maximum batch size for single requests to prevent overwhelming MCP
  private readonly MAX_BATCH_SIZE = 100;

  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
  ) {}

  /**
   * Get plan details by plan ID
   */
  getPlanDetails(planId: PlanId): PlanDetails {
    return PLANS[planId];
  }

  /**
   * Check if quota reset is needed and apply it
   */
  async resetQuotaIfApplicable(user: User): Promise<User> {
    const plan = this.getPlanDetails(user.plan);
    const now = new Date();
    
    // If no lastQuotaResetAt, initialize it
    if (!user.lastQuotaResetAt) {
      user.lastQuotaResetAt = now;
      user.currentLeadQuotaUsed = 0;
      return await this.userRepository.save(user);
    }

    const timeSinceReset = now.getTime() - user.lastQuotaResetAt.getTime();
    let shouldReset = false;

    switch (plan.period) {
      case 'day': {
        const lastReset = new Date(user.lastQuotaResetAt);
        lastReset.setHours(0, 0, 0, 0);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        shouldReset = today.getTime() > lastReset.getTime();
        break;
      }
      case 'week': {
        const lastReset = new Date(user.lastQuotaResetAt);
        const today = new Date();

        const lastResetWeekStart = new Date(lastReset);
        lastResetWeekStart.setDate(lastReset.getDate() - lastReset.getDay());
        lastResetWeekStart.setHours(0, 0, 0, 0);

        const todayWeekStart = new Date(today);
        todayWeekStart.setDate(today.getDate() - today.getDay());
        todayWeekStart.setHours(0, 0, 0, 0);

        shouldReset = todayWeekStart.getTime() > lastResetWeekStart.getTime();
        break;
      }
      case 'month': {
        // Reset if we're in a different month
        const resetDate = new Date(user.lastQuotaResetAt);
        shouldReset = now.getMonth() !== resetDate.getMonth() || 
                     now.getFullYear() !== resetDate.getFullYear();
        break;
      }
    }

    if (shouldReset) {
      this.logger.log(`Resetting quota for user ${user.id}, plan: ${user.plan}`);
      user.currentLeadQuotaUsed = 0;
      user.lastQuotaResetAt = now;
      return await this.userRepository.save(user);
    }

    return user;
  }

  /**
   * Get remaining quota for a user
   */
  async getRemainingQuota(userId: string): Promise<number> {
    const user = await this.userRepository.findOne({ where: { id: userId } });
    if (!user) {
      throw new Error(`User ${userId} not found`);
    }

    const updatedUser = await this.resetQuotaIfApplicable(user);
    const plan = this.getPlanDetails(updatedUser.plan);
    
    // Handle infinite quota
    if (plan.quota === Infinity) {
      return Number.MAX_SAFE_INTEGER;
    }

    const remaining = plan.quota - updatedUser.currentLeadQuotaUsed;
    return Math.max(0, remaining);
  }

  /**
   * Consume quota after leads are generated
   */
  async consumeQuota(userId: string, leadsGenerated: number): Promise<void> {
    const user = await this.userRepository.findOne({ where: { id: userId } });
    if (!user) {
      throw new Error(`User ${userId} not found`);
    }

    const updatedUser = await this.resetQuotaIfApplicable(user);
    updatedUser.currentLeadQuotaUsed += leadsGenerated;
    
    await this.userRepository.save(updatedUser);
    this.logger.log(`Consumed ${leadsGenerated} quota for user ${userId}. New usage: ${updatedUser.currentLeadQuotaUsed}`);
  }

  /**
   * Check if user can start prospecting (has remaining quota and not in cooldown)
   */
  async canStartProspecting(userId: string): Promise<boolean> {
    const remainingQuota = await this.getRemainingQuota(userId);
    return remainingQuota > 0;
  }

  /**
   * Check if user can start prospecting considering both quota and cooldown
   */
  async canStartProspectingWithCooldown(userId: string, usersService: any): Promise<{
    canStart: boolean;
    reason?: string;
    cooldownUntil?: Date;
    remainingCooldownMs?: number;
  }> {
    // Check quota first
    const remainingQuota = await this.getRemainingQuota(userId);
    if (remainingQuota <= 0) {
      return {
        canStart: false,
        reason: 'quota_exhausted'
      };
    }

    // Check cooldown
    const isInCooldown = await usersService.isInProspectCooldown(userId);
    if (isInCooldown) {
      const remainingCooldownMs = await usersService.getRemainingCooldownTime(userId);
      const cooldownUntil = new Date(Date.now() + remainingCooldownMs);
      
      return {
        canStart: false,
        reason: 'cooldown_active',
        cooldownUntil,
        remainingCooldownMs
      };
    }

    return { canStart: true };
  }

  /**
   * Get maximum leads that can be requested in a single batch
   * Considers both user quota and system batch limits
   */
  async getMaxLeadsToRequest(userId: string): Promise<number> {
    const remainingQuota = await this.getRemainingQuota(userId);
    
    // Cap at reasonable batch size even if quota allows more
    return Math.min(remainingQuota, this.MAX_BATCH_SIZE);
  }

  /**
   * Get quota usage summary for a user
   */
  async getQuotaUsage(userId: string): Promise<{
    planId: PlanId;
    totalQuota: number;
    usedQuota: number;
    remainingQuota: number;
    resetPeriod: string;
    nextResetAt: Date;
  }> {
    const user = await this.userRepository.findOne({ where: { id: userId } });
    if (!user) {
      throw new Error(`User ${userId} not found`);
    }

    const updatedUser = await this.resetQuotaIfApplicable(user);
    const plan = this.getPlanDetails(updatedUser.plan);
    const remainingQuota = await this.getRemainingQuota(userId);

    // Calculate next reset date
    const nextResetAt = this.calculateNextResetDate(updatedUser.lastQuotaResetAt, plan.period);

    return {
      planId: updatedUser.plan,
      totalQuota: plan.quota,
      usedQuota: updatedUser.currentLeadQuotaUsed,
      remainingQuota,
      resetPeriod: plan.period,
      nextResetAt,
    };
  }

  private calculateNextResetDate(lastResetAt: Date, period: 'day' | 'week' | 'month'): Date {
    const nextReset = new Date(lastResetAt);
    
    switch (period) {
      case 'day':
        nextReset.setDate(nextReset.getDate() + 1);
        break;
      case 'week':
        nextReset.setDate(nextReset.getDate() + 7);
        break;
      case 'month':
        nextReset.setMonth(nextReset.getMonth() + 1);
        break;
    }
    
    return nextReset;
  }
}
