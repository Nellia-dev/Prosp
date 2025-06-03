import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AgentsController } from './agents.controller';
import { AgentsService } from './agents.service';
import { Agent } from '../../database/entities/agent.entity';
import { McpModule } from '../mcp/mcp.module';

@Module({
  imports: [
    TypeOrmModule.forFeature([Agent]),
    McpModule,
  ],
  controllers: [AgentsController],
  providers: [AgentsService],
  exports: [AgentsService],
})
export class AgentsModule {}
