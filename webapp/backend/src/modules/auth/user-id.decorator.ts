import { createParamDecorator, ExecutionContext } from '@nestjs/common';

/**
 * A custom parameter decorator to extract the user ID from the request object.
 * The user object is attached to the request by the JwtStrategy after validating
 * the JWT token.
 * 
 * @example
 * ```
 * @Get('profile')
 * getProfile(@UserId() userId: string) {
 *   // userId will be the ID of the authenticated user
 * }
 * ```
 */
export const UserId = createParamDecorator(
  (data: unknown, ctx: ExecutionContext): string => {
    const request = ctx.switchToHttp().getRequest();
    // The 'user' property is attached by Passport's AuthGuard -> JwtStrategy
    return request.user?.id;
  },
);