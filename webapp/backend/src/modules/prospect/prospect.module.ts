import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bull';
import { ProspectService } from './prospect.service';
import { ProspectController } from './prospect.controller';
import { BusinessContextModule } from '../business-context/business-context.module';
import { McpModule } from '../mcp/mcp.module';
import { UsersModule } from '../users/users.module';
import { QuotaModule } from '../quota/quota.module';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [
    // Queue for prospect processing
    BullModule.registerQueue({
      name: 'prospect-processing',
    }),
    // Required modules
    BusinessContextModule,
    McpModule,
    UsersModule,
    QuotaModule,
    AuthModule,
  ],
  controllers: [ProspectController],
  providers: [ProspectService],
  exports: [ProspectService],
})
export class ProspectModule {}
