import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bull';
import { ProspectService } from './prospect.service';
import { ProspectController } from './prospect.controller';
import { BusinessContextModule } from '../business-context/business-context.module';
import { McpModule } from '../mcp/mcp.module';
import { UsersModule } from '../users/users.module';
import { QuotaModule } from '../quota/quota.module';
import { AuthModule } from '../auth/auth.module';
import { LeadsModule } from '../leads/leads.module';
import { ProspectProcessor } from '../queue/processors/prospect.processor';
import { WebSocketModule } from '../websocket/websocket.module';

@Module({
  imports: [
    BullModule.registerQueue({
      name: 'prospect-processing',
    },
    {
      name: 'enrichment-processing',
    }),
    BusinessContextModule,
    McpModule,
    UsersModule,
    QuotaModule,
    AuthModule,
    WebSocketModule,
    LeadsModule,
  ],
  controllers: [ProspectController],
  providers: [ProspectService, ProspectProcessor],
  exports: [ProspectService],
})
export class ProspectModule {}
