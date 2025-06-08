import { Module, forwardRef } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { BusinessContextEntity } from '../../database/entities/business-context.entity';
import { BusinessContextService } from './business-context.service';
import { BusinessContextController } from './business-context.controller';
import { McpModule } from '../mcp/mcp.module';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [
    TypeOrmModule.forFeature([BusinessContextEntity]),
    forwardRef(() => McpModule),
    AuthModule
  ],
  controllers: [BusinessContextController],
  providers: [BusinessContextService],
  exports: [BusinessContextService],
})
export class BusinessContextModule {}
