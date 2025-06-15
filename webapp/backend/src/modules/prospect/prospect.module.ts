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
import { EnrichmentProcessor } from '../queue/processors/enrichment.processor';
import { WebSocketModule } from '../websocket/websocket.module';
import { QueueModule } from '../queue/queue.module';
// import { McpWebhookModule } from '../mcp-webhook/mcp-webhook.module';

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
    // McpWebhookModule,
    QueueModule,
    UsersModule,
    QuotaModule,
    AuthModule,
    WebSocketModule,
    LeadsModule,
  ],
  controllers: [ProspectController],
  providers: [ProspectService, ProspectProcessor, EnrichmentProcessor],
  exports: [ProspectService],
})
export class ProspectModule {}
