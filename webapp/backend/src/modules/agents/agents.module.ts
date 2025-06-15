import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Agent } from '../../database/entities/agent.entity';
import { AgentsService } from './agents.service';
import { AgentsController } from './agents.controller';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [TypeOrmModule.forFeature([Agent]), AuthModule],
  providers: [AgentsService],
  controllers: [AgentsController],
  exports: [AgentsService, TypeOrmModule],
})
export class AgentsModule {}
