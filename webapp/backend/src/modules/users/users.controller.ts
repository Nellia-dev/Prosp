import { Controller, Get, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { UsersService } from './users.service';
import { QuotaService } from '../quota/quota.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { UserId } from '../auth/user-id.decorator';
import { UserPlanStatusResponse } from '../../shared/types/nellia.types';
import { PLANS } from '../../config/plans.config';

@ApiBearerAuth()
@ApiTags('Users')
@Controller('users')
@UseGuards(JwtAuthGuard)
export class UsersController {
  constructor(
    private readonly usersService: UsersService,
    private readonly quotaService: QuotaService,
  ) {}

  @Get('plan-status')
  @ApiOperation({ summary: 'Get user plan status with cooldown information' })
  @ApiResponse({ status: 200, description: 'User plan status retrieved successfully' })
  async getPlanStatus(@UserId() userId: string): Promise<UserPlanStatusResponse> {
    const user = await this.usersService.getUserById(userId);
    const quotaUsage = await this.quotaService.getQuotaUsage(userId);
    const prospectingStatus = await this.quotaService.canStartProspectingWithCooldown(userId, this.usersService);
    
    // Get cooldown information
    const isInCooldown = await this.usersService.isInProspectCooldown(userId);
    const remainingCooldownMs = await this.usersService.getRemainingCooldownTime(userId);
    
    const cooldownInfo = isInCooldown ? {
      isActive: true,
      cooldownUntil: user.prospectCooldownUntil?.toISOString(),
      remainingMs: remainingCooldownMs,
      remainingHours: Math.ceil(remainingCooldownMs / (1000 * 60 * 60)),
    } : {
      isActive: false,
    };

    return {
      plan: {
        id: user.plan,
        name: PLANS[user.plan].name,
        quota: PLANS[user.plan].quota,
        period: PLANS[user.plan].period,
      },
      quota: {
        total: quotaUsage.totalQuota,
        used: quotaUsage.usedQuota,
        remaining: quotaUsage.remainingQuota,
        nextResetAt: quotaUsage.nextResetAt.toISOString(),
      },
      canStartProspecting: prospectingStatus.canStart,
      hasActiveJob: !!user.prospectingJobId,
      activeJobId: user.prospectingJobId || undefined,
      cooldown: cooldownInfo,
    };
  }
}
