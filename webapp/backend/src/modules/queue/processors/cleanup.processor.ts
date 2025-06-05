import { Processor, Process } from '@nestjs/bull';
import { Logger } from '@nestjs/common';
import { Job } from 'bull';
import { InjectDataSource } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';

export interface CleanupJobData {
  type: 'old_logs' | 'completed_jobs' | 'old_chat_messages' | 'temp_files';
  daysOld?: number;
}

@Processor('cleanup')
export class CleanupProcessor {
  private readonly logger = new Logger(CleanupProcessor.name);

  constructor(
    @InjectDataSource()
    private dataSource: DataSource,
  ) {}

  @Process('cleanup-old-data')
  async handleDataCleanup(job: Job<CleanupJobData>) {
    const { type, daysOld = 30 } = job.data;
    
    this.logger.log(`Starting cleanup of ${type} older than ${daysOld} days`);

    try {
      let deletedCount = 0;

      switch (type) {
        case 'old_logs':
          deletedCount = await this.cleanupOldLogs(daysOld);
          break;

        case 'completed_jobs':
          deletedCount = await this.cleanupCompletedJobs(daysOld);
          break;

        case 'old_chat_messages':
          deletedCount = await this.cleanupOldChatMessages(daysOld);
          break;

        case 'temp_files':
          deletedCount = await this.cleanupTempFiles(daysOld);
          break;

        default:
          throw new Error(`Unknown cleanup type: ${type}`);
      }

      this.logger.log(`Successfully cleaned up ${deletedCount} items of type ${type}`);
      return { deletedCount, type };
    } catch (error) {
      this.logger.error(`Failed to cleanup ${type}`, error.stack);
      throw error;
    }
  }

  @Process('vacuum-database')
  async handleDatabaseVacuum(job: Job<{ analyze?: boolean }>) {
    const { analyze = true } = job.data;
    
    this.logger.log('Starting database vacuum operation');

    try {
      // Run VACUUM on PostgreSQL to reclaim space
      await this.dataSource.query('VACUUM');
      
      if (analyze) {
        await this.dataSource.query('ANALYZE');
      }

      this.logger.log('Database vacuum completed successfully');
    } catch (error) {
      this.logger.error('Database vacuum failed', error.stack);
      throw error;
    }
  }

  @Process('cleanup-expired-sessions')
  async handleSessionCleanup(job: Job<{}>) {
    this.logger.log('Starting expired session cleanup');

    try {
      // Clean up expired user sessions (if we had a sessions table)
      const result = await this.dataSource.query(`
        UPDATE users 
        SET last_login = NULL 
        WHERE last_login < NOW() - INTERVAL '7 days'
        AND last_login IS NOT NULL
      `);

      this.logger.log(`Cleaned up ${result.length} expired sessions`);
      return { cleanedSessions: result.length };
    } catch (error) {
      this.logger.error('Session cleanup failed', error.stack);
      throw error;
    }
  }

  private async cleanupOldLogs(daysOld: number): Promise<number> {
    // This would typically clean up application logs stored in database
    // For now, we'll just log the operation
    this.logger.log(`Would clean up logs older than ${daysOld} days`);
    return 0;
  }

  private async cleanupCompletedJobs(daysOld: number): Promise<number> {
    // This would clean up old job records from Bull queues
    // For now, we'll just log the operation
    this.logger.log(`Would clean up completed jobs older than ${daysOld} days`);
    return 0;
  }

  private async cleanupOldChatMessages(daysOld: number): Promise<number> {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - daysOld);

      const result = await this.dataSource.query(`
        DELETE FROM chat_messages 
        WHERE created_at < $1
      `, [cutoffDate]);

      return result.rowCount || 0;
    } catch (error) {
      this.logger.error('Failed to cleanup old chat messages', error);
      return 0;
    }
  }

  private async cleanupTempFiles(daysOld: number): Promise<number> {
    // This would clean up temporary files from the filesystem
    // For now, we'll just log the operation
    this.logger.log(`Would clean up temporary files older than ${daysOld} days`);
    return 0;
  }
}