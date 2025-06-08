import { Controller, Post, Body, ValidationPipe, UsePipes, HttpCode, BadRequestException } from '@nestjs/common';
import { McpWebhookService, WebhookPayload } from './mcp-webhook.service';
import { Logger } from '@nestjs/common';
import { Public } from '../auth/public.decorator';

@Public()
@Controller('mcp/webhook')
export class McpWebhookController {
  private readonly logger = new Logger(McpWebhookController.name);

  constructor(private readonly webhookService: McpWebhookService) {}

  @Post('job-complete')
  @HttpCode(200) // Respond immediately with 200 OK, processing happens async
  @UsePipes(new ValidationPipe({ transform: true, whitelist: true }))
  async handleJobCompletion(@Body() payload: WebhookPayload): Promise<{ status: string }> {
    this.logger.log(`Received webhook for job_id: ${payload.job_id}`);

    // Basic validation
    if (!payload.job_id || !payload.user_id || !payload.status) {
      throw new BadRequestException('Invalid webhook payload. Missing job_id, user_id, or status.');
    }

    // Don't await this. The service will handle the processing asynchronously.
    this.webhookService.processCompletedJob(payload);

    return { status: 'webhook received' };
  }
}