import {
  Controller,
  Get,
  Post,
  Delete,
  Body,
  Param,
  Query,
  HttpStatus,
  HttpException,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBody, ApiParam, ApiQuery, ApiBearerAuth } from '@nestjs/swagger';
import { ChatService } from './chat.service';
import { ChatMessage } from '../../shared/types/nellia.types';

interface SendMessageDto {
  content: string;
  attachments?: string[];
}

interface SearchMessagesDto {
  query: string;
  limit?: number;
}

interface DateRangeDto {
  startDate: string;
  endDate: string;
}

@ApiBearerAuth()
@ApiTags('chat')
@Controller('chat')
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Get(':agentId/history')
  @ApiOperation({ summary: 'Get message history for an agent' })
  @ApiParam({ name: 'agentId', description: 'Agent ID' })
  @ApiQuery({ name: 'limit', required: false, description: 'Number of messages to retrieve', type: Number })
  @ApiQuery({ name: 'offset', required: false, description: 'Offset for pagination', type: Number })
  @ApiResponse({
    status: 200,
    description: 'Message history retrieved successfully',
  })
  async getMessageHistory(
    @Param('agentId') agentId: string,
    @Query('limit') limit?: number,
    @Query('offset') offset?: number,
  ): Promise<ChatMessage[]> {
    return this.chatService.getMessageHistory(
      agentId,
      limit ? parseInt(limit.toString()) : 50,
      offset ? parseInt(offset.toString()) : 0,
    );
  }

  @Post(':agentId/send')
  @ApiOperation({ summary: 'Send a message to an agent' })
  @ApiParam({ name: 'agentId', description: 'Agent ID' })
  @ApiBody({ description: 'Message data' })
  @ApiResponse({
    status: 201,
    description: 'Message sent successfully',
  })
  @ApiResponse({
    status: 400,
    description: 'Invalid message data',
  })
  async sendMessage(
    @Param('agentId') agentId: string,
    @Body() sendMessageDto: SendMessageDto,
  ): Promise<ChatMessage> {
    if (!sendMessageDto.content || sendMessageDto.content.trim().length === 0) {
      throw new HttpException(
        {
          status: HttpStatus.BAD_REQUEST,
          error: 'Message content cannot be empty',
        },
        HttpStatus.BAD_REQUEST,
      );
    }

    return this.chatService.sendMessage(
      agentId,
      sendMessageDto.content,
      sendMessageDto.attachments,
    );
  }

  @Get('conversations')
  @ApiOperation({ summary: 'Get all agent conversations summary' })
  @ApiResponse({
    status: 200,
    description: 'Conversations retrieved successfully',
  })
  async getAgentConversations(): Promise<{
    agent_id: string;
    last_message: ChatMessage;
    message_count: number;
  }[]> {
    return this.chatService.getAgentConversations();
  }

  @Delete(':agentId/clear')
  @ApiOperation({ summary: 'Clear conversation history for an agent' })
  @ApiParam({ name: 'agentId', description: 'Agent ID' })
  @ApiResponse({
    status: 200,
    description: 'Conversation cleared successfully',
  })
  async clearConversation(
    @Param('agentId') agentId: string,
  ): Promise<{ success: boolean }> {
    const success = await this.chatService.clearConversation(agentId);
    return { success };
  }

  @Delete('messages/:messageId')
  @ApiOperation({ summary: 'Delete a specific message' })
  @ApiParam({ name: 'messageId', description: 'Message ID' })
  @ApiResponse({
    status: 200,
    description: 'Message deleted successfully',
  })
  @ApiResponse({
    status: 404,
    description: 'Message not found',
  })
  async deleteMessage(
    @Param('messageId') messageId: string,
  ): Promise<{ success: boolean }> {
    const success = await this.chatService.deleteMessage(messageId);
    return { success };
  }

  @Post(':agentId/search')
  @ApiOperation({ summary: 'Search messages for an agent' })
  @ApiParam({ name: 'agentId', description: 'Agent ID' })
  @ApiBody({ description: 'Search parameters' })
  @ApiResponse({
    status: 200,
    description: 'Search results retrieved successfully',
  })
  async searchMessages(
    @Param('agentId') agentId: string,
    @Body() searchDto: SearchMessagesDto,
  ): Promise<ChatMessage[]> {
    if (!searchDto.query || searchDto.query.trim().length === 0) {
      throw new HttpException(
        {
          status: HttpStatus.BAD_REQUEST,
          error: 'Search query cannot be empty',
        },
        HttpStatus.BAD_REQUEST,
      );
    }

    return this.chatService.searchMessages(
      agentId,
      searchDto.query,
      searchDto.limit || 20,
    );
  }

  @Post(':agentId/messages/date-range')
  @ApiOperation({ summary: 'Get messages within a date range' })
  @ApiParam({ name: 'agentId', description: 'Agent ID' })
  @ApiBody({ description: 'Date range parameters' })
  @ApiResponse({
    status: 200,
    description: 'Messages retrieved successfully',
  })
  async getMessagesByDateRange(
    @Param('agentId') agentId: string,
    @Body() dateRangeDto: DateRangeDto,
  ): Promise<ChatMessage[]> {
    const startDate = new Date(dateRangeDto.startDate);
    const endDate = new Date(dateRangeDto.endDate);

    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
      throw new HttpException(
        {
          status: HttpStatus.BAD_REQUEST,
          error: 'Invalid date format',
        },
        HttpStatus.BAD_REQUEST,
      );
    }

    if (startDate > endDate) {
      throw new HttpException(
        {
          status: HttpStatus.BAD_REQUEST,
          error: 'Start date must be before end date',
        },
        HttpStatus.BAD_REQUEST,
      );
    }

    return this.chatService.getMessagesByDateRange(agentId, startDate, endDate);
  }

  @Get(':agentId/export')
  @ApiOperation({ summary: 'Export conversation history' })
  @ApiParam({ name: 'agentId', description: 'Agent ID' })
  @ApiResponse({
    status: 200,
    description: 'Conversation exported successfully',
  })
  async exportConversation(
    @Param('agentId') agentId: string,
  ): Promise<{ messages: ChatMessage[]; metadata: any }> {
    return this.chatService.exportConversation(agentId);
  }
}
