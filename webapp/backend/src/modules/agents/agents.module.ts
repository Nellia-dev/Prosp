import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Agent } from '../../database/entities/agent.entity';
import { AgentsService } from './agents.service';
import { AgentsController } from './agents.controller';

@Module({
  imports: [TypeOrmModule.forFeature([Agent])],
  providers: [AgentsService],
  controllers: [AgentsController],
  exports: [AgentsService, TypeOrmModule],
})
export class AgentsModule {}
