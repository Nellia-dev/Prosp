import { Injectable, Logger } from '@nestjs/common';
import { InjectDataSource } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';

@Injectable()
export class DatabaseHealthCheckService {
  private readonly logger = new Logger(DatabaseHealthCheckService.name);

  constructor(
    @InjectDataSource()
    private dataSource: DataSource,
  ) {}

  async checkConnection(): Promise<{
    isConnected: boolean;
    error?: string;
    details: {
      database: string;
      host: string;
      port: number;
      connectionPoolSize?: number;
    };
  }> {
    try {
      // Test basic connection
      await this.dataSource.query('SELECT 1');
      
      // Get connection details
      const options = this.dataSource.options as any;
      
      this.logger.log('Database connection successful');
      
      return {
        isConnected: true,
        details: {
          database: options.database,
          host: options.host,
          port: options.port,
          connectionPoolSize: options.extra?.max || 10,
        },
      };
    } catch (error) {
      this.logger.error('Database connection failed', error.stack);
      
      return {
        isConnected: false,
        error: error.message,
        details: {
          database: 'unknown',
          host: 'unknown',
          port: 0,
        },
      };
    }
  }

  async checkMigrations(): Promise<{
    pendingMigrations: string[];
    executedMigrations: string[];
    needsMigration: boolean;
  }> {
    try {
      const pendingMigrations = await this.dataSource.showMigrations();
      
      // Get executed migrations from the migrations table
      let executedMigrations: string[] = [];
      try {
        const migrations = await this.dataSource.query(`
          SELECT name FROM migrations ORDER BY timestamp
        `);
        executedMigrations = migrations.map(m => m.name);
      } catch (e) {
        // Migrations table might not exist yet
        this.logger.warn('Could not query migrations table');
      }
      
      return {
        pendingMigrations: pendingMigrations ? ['Pending migrations detected'] : [],
        executedMigrations,
        needsMigration: pendingMigrations,
      };
    } catch (error) {
      this.logger.error('Migration check failed', error.stack);
      throw new Error(`Migration check failed: ${error.message}`);
    }
  }

  async getConnectionPoolStats(): Promise<{
    activeConnections: number;
    idleConnections: number;
    totalConnections: number;
  }> {
    try {
      // Query for connection statistics
      const result = await this.dataSource.query(`
        SELECT 
          count(*) FILTER (WHERE state = 'active') as active_connections,
          count(*) FILTER (WHERE state = 'idle') as idle_connections,
          count(*) as total_connections
        FROM pg_stat_activity 
        WHERE datname = current_database()
      `);

      return {
        activeConnections: parseInt(result[0]?.active_connections || '0'),
        idleConnections: parseInt(result[0]?.idle_connections || '0'),
        totalConnections: parseInt(result[0]?.total_connections || '0'),
      };
    } catch (error) {
      this.logger.warn('Could not get connection pool stats', error.message);
      return {
        activeConnections: 0,
        idleConnections: 0,
        totalConnections: 0,
      };
    }
  }

  async validateDatabaseStructure(): Promise<{
    tablesExist: boolean;
    missingTables: string[];
    allTablesPresent: string[];
  }> {
    const expectedTables = ['users', 'agents', 'leads', 'business_context', 'chat_messages'];
    
    try {
      const existingTables = await this.dataSource.query(`
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
      `);

      const existingTableNames = existingTables.map(t => t.table_name);
      const missingTables = expectedTables.filter(table => !existingTableNames.includes(table));
      const presentTables = expectedTables.filter(table => existingTableNames.includes(table));

      return {
        tablesExist: missingTables.length === 0,
        missingTables,
        allTablesPresent: presentTables,
      };
    } catch (error) {
      this.logger.error('Database structure validation failed', error.stack);
      throw new Error(`Structure validation failed: ${error.message}`);
    }
  }
}