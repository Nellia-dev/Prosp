import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { MetricsService } from './metrics.service';
import { MetricsController } from './metrics.controller';
import { Agent } from '../../database/entities/agent.entity';
import { Lead } from '../../database/entities/lead.entity';
import { ChatMessage } from '../../database/entities/chat-message.entity';

@Module({
  imports: [
    TypeOrmModule.forFeature([Agent, Lead, ChatMessage]),
  ],
  controllers: [MetricsController],
  providers: [MetricsService],
  exports: [MetricsService],
})
export class MetricsModule {}
