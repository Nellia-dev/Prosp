import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { BullModule } from '@nestjs/bull';
import { LeadProcessingProcessor } from './processors/lead-processing.processor';
import { EnrichmentProcessor } from './processors/enrichment.processor';
import { MetricsCollectionProcessor } from './processors/metrics-collection.processor';
import { CleanupProcessor } from './processors/cleanup.processor';
import { QueueService } from './queue.service';
import { QueueController } from './queue.controller';
import { AgentsModule } from '../agents/agents.module';
import { LeadsModule } from '../leads/leads.module';
import { MetricsModule } from '../metrics/metrics.module';
import { McpModule } from '../mcp/mcp.module';
import { WebSocketModule } from '../websocket/websocket.module';
import { BusinessContextModule } from '../business-context/business-context.module';
import { UsersModule } from '../users/users.module';
import { QuotaModule } from '../quota/quota.module';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [
    // Register Bull queues
    BullModule.registerQueue(
      {
        name: 'prospect-processing',
        defaultJobOptions: {
          removeOnComplete: 50, // Keep last 50 completed jobs
          removeOnFail: 25, // Keep last 25 failed jobs
          attempts: 3,
          backoff: {
            type: 'exponential',
            delay: 2000,
          },
        },
      },
      {
        name: 'enrichment-processing',
        defaultJobOptions: {
          removeOnComplete: 50,
          removeOnFail: 25,
          attempts: 2,
          backoff: {
            type: 'exponential',
            delay: 5000,
          },
        },
      },
      {
        name: 'metrics-collection',
        defaultJobOptions: {
          removeOnComplete: 20,
          removeOnFail: 10,
          attempts: 2,
          backoff: {
            type: 'fixed',
            delay: 5000,
          },
        },
      },
      {
        name: 'cleanup',
        defaultJobOptions: {
          removeOnComplete: 10,
          removeOnFail: 5,
          attempts: 1,
        },
      },
    ),
    
    // Import required modules
    AgentsModule,
    LeadsModule,
    MetricsModule,
    McpModule,
    WebSocketModule,
    HttpModule,
    BusinessContextModule,
    UsersModule,
    QuotaModule,
    AuthModule,
  ],
  providers: [
    LeadProcessingProcessor,
    EnrichmentProcessor,
    MetricsCollectionProcessor,
    CleanupProcessor,
    QueueService,
  ],
  controllers: [QueueController],
  exports: [QueueService],
})
export class QueueModule {}
