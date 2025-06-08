import {
  Controller,
  Post,
  Get,
  Put,
  Delete,
  Body,
  Request,
  UseGuards,
  HttpCode,
  HttpStatus,
  ValidationPipe,
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiBearerAuth,
  ApiBody,
} from '@nestjs/swagger';
import { IsEmail, IsString, MinLength, IsNotEmpty } from 'class-validator';
import { AuthService, LoginDto, RegisterDto, ChangePasswordDto, AuthResponse } from './auth.service';
import { User, UserRole } from '../../database/entities/user.entity';
import { Roles } from './roles.decorator';
import { RolesGuard } from './roles.guard';
import { Public } from './public.decorator';

// DTOs for validation
class LoginRequestDto implements LoginDto {
  @IsEmail()
  @IsNotEmpty()
  email: string;

  @IsString()
  @IsNotEmpty()
  password: string;
}

class RegisterRequestDto implements RegisterDto {
  @IsEmail()
  @IsNotEmpty()
  email: string;

  @IsString()
  @MinLength(8)
  @IsNotEmpty()
  password: string;

  @IsString()
  @IsNotEmpty()
  firstName: string;

  @IsString()
  @IsNotEmpty()
  lastName: string;
}

class ChangePasswordRequestDto implements ChangePasswordDto {
  @IsString()
  @IsNotEmpty()
  currentPassword: string;

  @IsString()
  @MinLength(8)
  @IsNotEmpty()
  newPassword: string;
}

class UpdateProfileDto {
  @IsString()
  @IsNotEmpty()
  firstName?: string;

  @IsString()
  @IsNotEmpty()
  lastName?: string;
}

class UpdateUserRoleDto {
  @IsString()
  @IsNotEmpty()
  role: UserRole;
}

@ApiTags('Authentication')
@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Public()
  @Post('login')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'User login' })
  @ApiResponse({
    status: 200,
    description: 'Login successful',
    type: Object,
  })
  @ApiResponse({ status: 401, description: 'Invalid credentials' })
  async login(
    @Body(ValidationPipe) loginDto: LoginRequestDto,
  ): Promise<AuthResponse> {
    return this.authService.login(loginDto);
  }

  @Public()
  @Post('register')
  @HttpCode(HttpStatus.CREATED)
  @ApiOperation({ summary: 'User registration' })
  @ApiResponse({
    status: 201,
    description: 'Registration successful',
    type: Object,
  })
  @ApiResponse({ status: 409, description: 'User already exists' })
  @ApiResponse({ status: 400, description: 'Invalid input data' })
  async register(
    @Body(ValidationPipe) registerDto: RegisterRequestDto,
  ): Promise<AuthResponse> {
    return this.authService.register(registerDto);
  }

  @Get('profile')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Get user profile' })
  @ApiResponse({
    status: 200,
    description: 'User profile retrieved successfully',
    type: User,
  })
  @ApiResponse({ status: 401, description: 'Unauthorized' })
  @ApiResponse({ status: 404, description: 'User not found' })
  async getProfile(@Request() req): Promise<User> {
    return this.authService.getProfile(req.user.id);
  }

  @Put('profile')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Update user profile' })
  @ApiResponse({
    status: 200,
    description: 'Profile updated successfully',
    type: User,
  })
  @ApiResponse({ status: 401, description: 'Unauthorized' })
  @ApiResponse({ status: 404, description: 'User not found' })
  async updateProfile(
    @Request() req,
    @Body(ValidationPipe) updateProfileDto: UpdateProfileDto,
  ): Promise<User> {
    return this.authService.updateProfile(req.user.id, updateProfileDto);
  }

  @Put('change-password')
  @ApiBearerAuth()
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Change user password' })
  @ApiResponse({ status: 200, description: 'Password changed successfully' })
  @ApiResponse({ status: 401, description: 'Unauthorized or invalid current password' })
  @ApiResponse({ status: 400, description: 'Invalid new password' })
  async changePassword(
    @Request() req,
    @Body(ValidationPipe) changePasswordDto: ChangePasswordRequestDto,
  ): Promise<{ message: string }> {
    await this.authService.changePassword(req.user.id, changePasswordDto);
    return { message: 'Password changed successfully' };
  }

  @Delete('deactivate')
  @ApiBearerAuth()
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Deactivate user account' })
  @ApiResponse({ status: 200, description: 'Account deactivated successfully' })
  @ApiResponse({ status: 401, description: 'Unauthorized' })
  @ApiResponse({ status: 404, description: 'User not found' })
  async deactivateAccount(@Request() req): Promise<{ message: string }> {
    await this.authService.deactivateAccount(req.user.id);
    return { message: 'Account deactivated successfully' };
  }

  // Admin only endpoints
  @Get('users')
  @Roles(UserRole.ADMIN)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Get all users (Admin only)' })
  @ApiResponse({
    status: 200,
    description: 'Users retrieved successfully',
    type: [User],
  })
  @ApiResponse({ status: 401, description: 'Unauthorized' })
  @ApiResponse({ status: 403, description: 'Forbidden - Admin access required' })
  async getAllUsers(): Promise<User[]> {
    return this.authService.getAllUsers();
  }

  @Put('users/:userId/role')
  @Roles(UserRole.ADMIN)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Update user role (Admin only)' })
  @ApiResponse({
    status: 200,
    description: 'User role updated successfully',
    type: User,
  })
  @ApiResponse({ status: 401, description: 'Unauthorized' })
  @ApiResponse({ status: 403, description: 'Forbidden - Admin access required' })
  @ApiResponse({ status: 404, description: 'User not found' })
  async updateUserRole(
    @Request() req,
    @Body(ValidationPipe) updateRoleDto: UpdateUserRoleDto,
  ): Promise<User> {
    const userId = req.params.userId;
    return this.authService.updateUserRole(userId, updateRoleDto.role);
  }

  @Get('validate-token')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Validate JWT token' })
  @ApiResponse({
    status: 200,
    description: 'Token is valid',
    schema: {
      type: 'object',
      properties: {
        valid: { type: 'boolean' },
        user: { type: 'object' },
      },
    },
  })
  @ApiResponse({ status: 401, description: 'Invalid or expired token' })
  async validateToken(@Request() req): Promise<{ valid: boolean; user: User }> {
    return {
      valid: true,
      user: req.user,
    };
  }

  @Post('refresh-token')
  @ApiBearerAuth()
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Refresh JWT token' })
  @ApiResponse({
    status: 200,
    description: 'Token refreshed successfully',
    type: Object,
  })
  @ApiResponse({ status: 401, description: 'Invalid or expired token' })
  async refreshToken(@Request() req): Promise<{ access_token: string }> {
    const payload = {
      sub: req.user.id,
      email: req.user.email,
      role: req.user.role,
    };

    // This would typically involve checking if the token is close to expiry
    // For simplicity, we're just issuing a new token
    const access_token = this.authService['jwtService'].sign(payload);

    return { access_token };
  }
}
