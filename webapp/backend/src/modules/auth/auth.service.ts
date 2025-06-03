import {
  Injectable,
  UnauthorizedException,
  ConflictException,
  NotFoundException,
  BadRequestException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcrypt';
import { User, UserRole } from '../../database/entities/user.entity';

export interface LoginDto {
  email: string;
  password: string;
}

export interface RegisterDto {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
}

export interface ChangePasswordDto {
  currentPassword: string;
  newPassword: string;
}

export interface AuthResponse {
  access_token: string;
  user: {
    id: string;
    email: string;
    firstName: string;
    lastName: string;
    role: UserRole;
    isActive: boolean;
    lastLogin: Date;
  };
}

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(User)
    private userRepository: Repository<User>,
    private jwtService: JwtService,
  ) {}

  /**
   * Validate user credentials for local strategy
   */
  async validateUser(email: string, password: string): Promise<User | null> {
    try {
      const user = await this.userRepository.findOne({
        where: { email: email.toLowerCase() },
        select: ['id', 'email', 'password', 'first_name', 'last_name', 'role', 'is_active'],
      });

      if (!user) {
        return null;
      }

      if (!user.is_active) {
        throw new UnauthorizedException('Account is deactivated');
      }

      const isPasswordValid = await bcrypt.compare(password, user.password);
      if (!isPasswordValid) {
        return null;
      }

      // Remove password from returned user object
      const { password: _, ...result } = user;
      return result as User;
    } catch (error) {
      if (error instanceof UnauthorizedException) {
        throw error;
      }
      throw new UnauthorizedException('Invalid credentials');
    }
  }

  /**
   * Login user and return JWT token
   */
  async login(loginDto: LoginDto): Promise<AuthResponse> {
    const { email, password } = loginDto;

    const user = await this.validateUser(email, password);
    if (!user) {
      throw new UnauthorizedException('Invalid email or password');
    }

    // Update last login timestamp
    await this.userRepository.update(user.id, {
      last_login: new Date(),
    });

    const payload = {
      sub: user.id,
      email: user.email,
      role: user.role,
    };

    const access_token = this.jwtService.sign(payload);

    return {
      access_token,
      user: {
        id: user.id,
        email: user.email,
        firstName: user.first_name,
        lastName: user.last_name,
        role: user.role,
        isActive: user.is_active,
        lastLogin: user.last_login,
      },
    };
  }

  /**
   * Register new user
   */
  async register(registerDto: RegisterDto): Promise<AuthResponse> {
    const { email, password, firstName, lastName } = registerDto;

    // Check if user already exists
    const existingUser = await this.userRepository.findOne({
      where: { email: email.toLowerCase() },
    });

    if (existingUser) {
      throw new ConflictException('User with this email already exists');
    }

    // Validate password strength
    if (password.length < 8) {
      throw new BadRequestException('Password must be at least 8 characters long');
    }

    // Hash password
    const saltRounds = 12;
    const hashedPassword = await bcrypt.hash(password, saltRounds);

    // Create new user
    const newUser = this.userRepository.create({
      email: email.toLowerCase(),
      password: hashedPassword,
      first_name: firstName,
      last_name: lastName,
      role: UserRole.USER,
      is_active: true,
      last_login: new Date(),
    });

    const savedUser = await this.userRepository.save(newUser);

    // Generate JWT token
    const payload = {
      sub: savedUser.id,
      email: savedUser.email,
      role: savedUser.role,
    };

    const access_token = this.jwtService.sign(payload);

    return {
      access_token,
      user: {
        id: savedUser.id,
        email: savedUser.email,
        firstName: savedUser.first_name,
        lastName: savedUser.last_name,
        role: savedUser.role,
        isActive: savedUser.is_active,
        lastLogin: savedUser.last_login,
      },
    };
  }

  /**
   * Get user profile by ID
   */
  async getProfile(userId: string): Promise<User> {
    const user = await this.userRepository.findOne({
      where: { id: userId },
      select: ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'last_login', 'created_at'],
    });

    if (!user) {
      throw new NotFoundException('User not found');
    }

    return user;
  }

  /**
   * Update user profile
   */
  async updateProfile(
    userId: string,
    updateData: { firstName?: string; lastName?: string },
  ): Promise<User> {
    const user = await this.userRepository.findOne({
      where: { id: userId },
    });

    if (!user) {
      throw new NotFoundException('User not found');
    }

    if (updateData.firstName) {
      user.first_name = updateData.firstName;
    }

    if (updateData.lastName) {
      user.last_name = updateData.lastName;
    }

    const updatedUser = await this.userRepository.save(user);
    
    // Remove password from response
    const { password, ...result } = updatedUser;
    return result as User;
  }

  /**
   * Change user password
   */
  async changePassword(userId: string, changePasswordDto: ChangePasswordDto): Promise<void> {
    const { currentPassword, newPassword } = changePasswordDto;

    const user = await this.userRepository.findOne({
      where: { id: userId },
      select: ['id', 'password'],
    });

    if (!user) {
      throw new NotFoundException('User not found');
    }

    // Verify current password
    const isCurrentPasswordValid = await bcrypt.compare(currentPassword, user.password);
    if (!isCurrentPasswordValid) {
      throw new UnauthorizedException('Current password is incorrect');
    }

    // Validate new password
    if (newPassword.length < 8) {
      throw new BadRequestException('New password must be at least 8 characters long');
    }

    if (newPassword === currentPassword) {
      throw new BadRequestException('New password must be different from current password');
    }

    // Hash new password
    const saltRounds = 12;
    const hashedNewPassword = await bcrypt.hash(newPassword, saltRounds);

    // Update password
    await this.userRepository.update(userId, {
      password: hashedNewPassword,
    });
  }

  /**
   * Deactivate user account
   */
  async deactivateAccount(userId: string): Promise<void> {
    const user = await this.userRepository.findOne({
      where: { id: userId },
    });

    if (!user) {
      throw new NotFoundException('User not found');
    }

    await this.userRepository.update(userId, {
      is_active: false,
    });
  }

  /**
   * Validate JWT payload (for JWT strategy)
   */
  async validateJwtPayload(payload: any): Promise<User> {
    const user = await this.userRepository.findOne({
      where: { id: payload.sub },
      select: ['id', 'email', 'first_name', 'last_name', 'role', 'is_active'],
    });

    if (!user || !user.is_active) {
      throw new UnauthorizedException('User not found or inactive');
    }

    return user;
  }

  /**
   * Get all users (admin only)
   */
  async getAllUsers(): Promise<User[]> {
    return this.userRepository.find({
      select: ['id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'last_login', 'created_at'],
      order: { created_at: 'DESC' },
    });
  }

  /**
   * Update user role (admin only)
   */
  async updateUserRole(userId: string, role: UserRole): Promise<User> {
    const user = await this.userRepository.findOne({
      where: { id: userId },
    });

    if (!user) {
      throw new NotFoundException('User not found');
    }

    await this.userRepository.update(userId, { role });

    return this.getProfile(userId);
  }
}
