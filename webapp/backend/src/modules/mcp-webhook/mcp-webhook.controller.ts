import { Controller, Post, Body, Logger, HttpException, HttpStatus } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse } from '@nestjs/swagger';
import { McpWebhookService, WebhookPayload } from './mcp-webhook.service';
import { Public } from '../auth/public.decorator';

@ApiTags('mcp-webhook')
@Controller('mcp/webhook')
export class McpWebhookController {
  private readonly logger = new Logger(McpWebhookController.name);

  constructor(private readonly webhookService: McpWebhookService) {}

  @Public()
  @Post('event-stream')
  @ApiOperation({ summary: 'Webhook for real-time events from MCP pipelines' })
  @ApiResponse({ status: 200, description: 'Event processed successfully' })
  async handleEventStream(@Body() event: any): Promise<{ status: string }> {
    const eventType = event.event_type || 'unknown_event';
    const jobId = event.job_id || 'unknown_job';
    this.logger.debug(`Received event-stream webhook for job ${jobId}, event: ${eventType}`);
    try {
      await this.webhookService.processStreamedEvent(event);
      return { status: 'received' };
    } catch (error) {
      this.logger.error(`Error processing event-stream webhook for job ${jobId}: ${error.message}`, error.stack);
      throw new HttpException('Error processing event webhook', HttpStatus.INTERNAL_SERVER_ERROR);
    }
  }
}