import { Module } from '@nestjs/common';
import { McpWebhookController } from './mcp-webhook.controller';
import { McpWebhookService } from './mcp-webhook.service';
import { LeadsModule } from '../leads/leads.module';
import { QuotaModule } from '../quota/quota.module';
import { UsersModule } from '../users/users.module';
import { WebSocketModule } from '../websocket/websocket.module';
import { BullModule } from '@nestjs/bull';

@Module({
  imports: [
    LeadsModule,
    QuotaModule,
    UsersModule,
    WebSocketModule,
    BullModule.registerQueue({
      name: 'enrichment-processing',
    }),
  ],
  controllers: [McpWebhookController],
  providers: [McpWebhookService],
})
export class McpWebhookModule {}