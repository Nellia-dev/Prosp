import { Module } from '@nestjs/common';
import { DatabaseHealthCheckService } from './health-check.service';

@Module({
  providers: [DatabaseHealthCheckService],
  exports: [DatabaseHealthCheckService],
})
export class DatabaseModule {}