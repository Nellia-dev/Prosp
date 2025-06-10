import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Lead } from '@/database/entities/lead.entity';
import { LeadsService } from './leads.service';
import { LeadsController } from './leads.controller';
import { AuthModule } from '../auth/auth.module';

@Module({
  imports: [TypeOrmModule.forFeature([Lead]), AuthModule],
  providers: [LeadsService],
  controllers: [LeadsController],
  exports: [LeadsService, TypeOrmModule],
})
export class LeadsModule {}
