import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { ChatMessage as ChatMessageEntity } from '../../database/entities/chat-message.entity';
import { McpService } from '../mcp/mcp.service';
import { 
  ChatMessage,
  AgentName,
} from '../../shared/types/nellia.types';

@Injectable()
export class ChatService {
  constructor(
    @InjectRepository(ChatMessageEntity)
    private chatMessageRepository: Repository<ChatMessageEntity>,
    private mcpService: McpService,
  ) {}

  async getMessageHistory(agentId: string, limit: number = 50, offset: number = 0): Promise<ChatMessage[]> {
    const messages = await this.chatMessageRepository.find({
      where: { agent_id: agentId },
      order: { timestamp: 'DESC' },
      take: limit,
      skip: offset,
    });

    return messages.map(this.entityToDto).reverse(); // Return in chronological order
  }

  async sendMessage(agentId: string, content: string, attachments?: string[]): Promise<ChatMessage> {
    // Save user message
    const userMessage = this.chatMessageRepository.create({
      agent_id: agentId,
      content,
      type: 'user',
      attachments: attachments || [],
      timestamp: new Date(),
    });

    const savedUserMessage = await this.chatMessageRepository.save(userMessage);

    try {
      // Send message to MCP server and get agent response
      const agentResponse = await this.mcpService.sendChatMessage(agentId as AgentName, content);

      // Save agent response
      const agentMessage = this.chatMessageRepository.create({
        agent_id: agentId,
        content: agentResponse,
        type: 'agent',
        attachments: [],
        timestamp: new Date(),
      });

      await this.chatMessageRepository.save(agentMessage);

      return this.entityToDto(savedUserMessage);
    } catch (error) {
      console.error('Failed to send message to MCP server:', error);
      
      // Save error response from agent
      const errorMessage = this.chatMessageRepository.create({
        agent_id: agentId,
        content: 'Sorry, I encountered an error while processing your message. Please try again.',
        type: 'agent',
        attachments: [],
        timestamp: new Date(),
      });

      await this.chatMessageRepository.save(errorMessage);

      return this.entityToDto(savedUserMessage);
    }
  }

  async getAgentConversations(): Promise<{ agent_id: string; last_message: ChatMessage; message_count: number }[]> {
    const conversations = await this.chatMessageRepository
      .createQueryBuilder('message')
      .select('message.agent_id', 'agent_id')
      .addSelect('COUNT(*)', 'message_count')
      .addSelect('MAX(message.timestamp)', 'last_timestamp')
      .groupBy('message.agent_id')
      .orderBy('last_timestamp', 'DESC')
      .getRawMany();

    const result = [];
    for (const conv of conversations) {
      const lastMessage = await this.chatMessageRepository.findOne({
        where: { agent_id: conv.agent_id },
        order: { timestamp: 'DESC' },
      });

      if (lastMessage) {
        result.push({
          agent_id: conv.agent_id,
          last_message: this.entityToDto(lastMessage),
          message_count: parseInt(conv.message_count),
        });
      }
    }

    return result;
  }

  async clearConversation(agentId: string): Promise<boolean> {
    const result = await this.chatMessageRepository.delete({ agent_id: agentId });
    
    // Notify MCP server about conversation reset
    try {
      await this.mcpService.sendChatMessage(agentId as AgentName, '[CLEAR_HISTORY]');
    } catch (error) {
      console.error('Failed to clear chat history in MCP server:', error);
    }

    return result.affected > 0;
  }

  async deleteMessage(messageId: string): Promise<boolean> {
    const message = await this.chatMessageRepository.findOne({
      where: { id: messageId },
    });

    if (!message) {
      throw new NotFoundException('Message not found');
    }

    await this.chatMessageRepository.remove(message);
    return true;
  }

  async searchMessages(agentId: string, query: string, limit: number = 20): Promise<ChatMessage[]> {
    const messages = await this.chatMessageRepository
      .createQueryBuilder('message')
      .where('message.agent_id = :agentId', { agentId })
      .andWhere('message.content ILIKE :query', { query: `%${query}%` })
      .orderBy('message.timestamp', 'DESC')
      .take(limit)
      .getMany();

    return messages.map(this.entityToDto);
  }

  async getMessagesByDateRange(
    agentId: string, 
    startDate: Date, 
    endDate: Date
  ): Promise<ChatMessage[]> {
    const messages = await this.chatMessageRepository
      .createQueryBuilder('message')
      .where('message.agent_id = :agentId', { agentId })
      .andWhere('message.timestamp >= :startDate', { startDate })
      .andWhere('message.timestamp <= :endDate', { endDate })
      .orderBy('message.timestamp', 'ASC')
      .getMany();

    return messages.map(this.entityToDto);
  }

  async exportConversation(agentId: string): Promise<{ messages: ChatMessage[]; metadata: any }> {
    const messages = await this.getMessageHistory(agentId, 1000); // Get all messages
    
    const metadata = {
      agent_id: agentId,
      exported_at: new Date().toISOString(),
      message_count: messages.length,
      date_range: {
        start: messages.length > 0 ? messages[0].timestamp : null,
        end: messages.length > 0 ? messages[messages.length - 1].timestamp : null,
      },
    };

    return { messages, metadata };
  }

  private entityToDto(entity: ChatMessageEntity): ChatMessage {
    return {
      id: entity.id,
      agent_id: entity.agent_id,
      content: entity.content,
      timestamp: entity.timestamp.toISOString(),
      type: entity.type,
      attachments: entity.attachments || [],
    };
  }
}
