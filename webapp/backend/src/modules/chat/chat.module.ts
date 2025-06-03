import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ChatMessage as ChatMessageEntity } from '../../database/entities/chat-message.entity';
import { ChatService } from './chat.service';
import { ChatController } from './chat.controller';
import { McpModule } from '../mcp/mcp.module';

@Module({
  imports: [
    TypeOrmModule.forFeature([ChatMessageEntity]),
    McpModule,
  ],
  controllers: [ChatController],
  providers: [ChatService],
  exports: [ChatService],
})
export class ChatModule {}
