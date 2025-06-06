import { Module, forwardRef } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { McpService } from './mcp.service';
import { McpController } from './mcp.controller';
import { BusinessContextModule } from '../business-context/business-context.module';

@Module({
  imports: [HttpModule, forwardRef(() => BusinessContextModule)],
  controllers: [McpController],
  providers: [McpService],
  exports: [McpService],
})
export class McpModule {}
