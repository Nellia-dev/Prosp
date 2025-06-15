import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bull';
import { QueueController } from './queue.controller';
import { QueueService } from './queue.service';
import { LeadsModule } from '../leads/leads.module';
import { QuotaModule } from '../quota/quota.module';
import { UsersModule } from '../users/users.module';
import { WebSocketModule } from '../websocket/websocket.module';

@Module({
  imports: [
    BullModule.registerQueue(
      { name: 'prospect-processing' },
      { name: 'enrichment-processing' },
      { name: 'metrics-collection' },
      { name: 'cleanup' },
    ),
    LeadsModule,
    QuotaModule,
    UsersModule,
    WebSocketModule,
  ],
  controllers: [QueueController],
  providers: [QueueService],
  exports: [QueueService],
})
export class QueueModule {}
