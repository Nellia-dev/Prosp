import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { McpService } from './mcp.service';
import { McpController } from './mcp.controller';

@Module({
  imports: [HttpModule],
  controllers: [McpController],
  providers: [McpService],
  exports: [McpService],
})
export class McpModule {}
