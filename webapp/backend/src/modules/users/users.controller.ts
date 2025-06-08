import { Controller, Get, Req, UseGuards } from '@nestjs/common';
import { Request } from 'express';
import { UsersService } from './users.service';
import { QuotaService } from '../quota/quota.service';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';

interface AuthenticatedRequest extends Request {
  user: {
    id: string;
    email: string;
  };
}

@ApiBearerAuth()
@ApiTags('Users')
@Controller('users')
export class UsersController {
  constructor(
    private readonly usersService: UsersService,
    private readonly quotaService: QuotaService,
  ) {}

  /**
   * Get current user's plan status and quota information
   */
  @Get('me/plan-status')
  async getPlanStatus(@Req() request: AuthenticatedRequest) {
    // For now, we'll use a mock user ID - replace with real auth when available
    const userId = request.user?.id || 'mock-user-id';
    
    try {
      const user = await this.usersService.getUserById(userId);
      const planDetails = this.quotaService.getPlanDetails(user.plan);
      const remainingQuota = await this.quotaService.getRemainingQuota(userId);
      const canStartProspecting = await this.quotaService.canStartProspecting(userId);
      
      // Calculate next reset date based on plan period
      const nextResetDate = this.calculateNextResetDate(user.lastQuotaResetAt, planDetails.period);
      
      return {
        success: true,
        data: {
          plan: {
            id: user.plan,
            name: planDetails.name,
            quota: planDetails.quota,
            period: planDetails.period,
            price: planDetails.price,
          },
          quota: {
            total: planDetails.quota,
            used: user.currentLeadQuotaUsed,
            remaining: remainingQuota,
            nextResetAt: nextResetDate,
          },
          canStartProspecting,
          hasActiveJob: !!user.prospectingJobId,
          activeJobId: user.prospectingJobId,
        },
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  private calculateNextResetDate(lastResetAt: Date, period: 'day' | 'week' | 'month'): Date {
    if (!lastResetAt) {
      return new Date();
    }

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
