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
   * Clear the prospecting job ID when job completes
   */
  async clearProspectingJob(userId: string): Promise<User> {
    const user = await this.getUserById(userId);
    
    user.prospectingJobId = null;
    
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
