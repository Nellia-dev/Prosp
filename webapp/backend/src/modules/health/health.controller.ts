import { Controller, Get } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse } from '@nestjs/swagger';
import { DatabaseHealthCheckService } from '../../database/health-check.service';

@ApiTags('Health')
@Controller('health')
export class HealthController {
  constructor(
    private readonly databaseHealthCheckService: DatabaseHealthCheckService,
  ) {}

  @Get()
  @ApiOperation({ summary: 'Get system health status' })
  @ApiResponse({ status: 200, description: 'System health status' })
  async getHealthStatus() {
    const dbConnection = await this.databaseHealthCheckService.checkConnection();
    const dbStructure = await this.databaseHealthCheckService.validateDatabaseStructure();
    const connectionStats = await this.databaseHealthCheckService.getConnectionPoolStats();

    let migrationsStatus;
    try {
      migrationsStatus = await this.databaseHealthCheckService.checkMigrations();
    } catch (error) {
      migrationsStatus = {
        pendingMigrations: [],
        executedMigrations: [],
        needsMigration: true,
        error: error.message,
      };
    }

    return {
      status: dbConnection.isConnected ? 'healthy' : 'unhealthy',
      timestamp: new Date().toISOString(),
      services: {
        database: {
          status: dbConnection.isConnected ? 'up' : 'down',
          details: dbConnection.details,
          error: dbConnection.error,
          structure: dbStructure,
          connectionPool: connectionStats,
          migrations: migrationsStatus,
        },
      },
    };
  }

  @Get('database')
  @ApiOperation({ summary: 'Get detailed database health status' })
  @ApiResponse({ status: 200, description: 'Database health details' })
  async getDatabaseHealth() {
    const connection = await this.databaseHealthCheckService.checkConnection();
    const structure = await this.databaseHealthCheckService.validateDatabaseStructure();
    const connectionStats = await this.databaseHealthCheckService.getConnectionPoolStats();

    let migrations;
    try {
      migrations = await this.databaseHealthCheckService.checkMigrations();
    } catch (error) {
      migrations = {
        pendingMigrations: [],
        executedMigrations: [],
        needsMigration: true,
        error: error.message,
      };
    }

    return {
      connection,
      structure,
      connectionStats,
      migrations,
      timestamp: new Date().toISOString(),
    };
  }

  @Get('ready')
  @ApiOperation({ summary: 'Check if application is ready to serve requests' })
  @ApiResponse({ status: 200, description: 'Application readiness status' })
  async getReadinessStatus() {
    const dbConnection = await this.databaseHealthCheckService.checkConnection();
    const dbStructure = await this.databaseHealthCheckService.validateDatabaseStructure();

    const isReady = dbConnection.isConnected && dbStructure.tablesExist;

    return {
      ready: isReady,
      timestamp: new Date().toISOString(),
      checks: {
        database_connected: dbConnection.isConnected,
        tables_exist: dbStructure.tablesExist,
        missing_tables: dbStructure.missingTables,
      },
    };
  }
}