import { ConfigService } from '@nestjs/config';
import { TypeOrmModuleOptions } from '@nestjs/typeorm';
import { DataSource, DataSourceOptions } from 'typeorm';

// This is likely used by TypeOrmModule.forRootAsync
export const databaseConfig = (configService: ConfigService): TypeOrmModuleOptions => {
  const dbOptions = {
    type: 'postgres' as const,
    host: configService.get('DB_HOST', 'localhost'),
    port: configService.get('DB_PORT', 5432),
    username: configService.get('DB_USERNAME', 'postgres'),
    password: configService.get('DB_PASSWORD', 'postgres'),
    database: configService.get('DB_DATABASE', 'nellia_prospector'),
    entities: [__dirname + '/../database/entities/*.entity{.ts,.js}'],
    migrations: [__dirname + '/../database/migrations/*{.ts,.js}'],
    synchronize: configService.get('NODE_ENV') === 'development',
    logging: configService.get('NODE_ENV') === 'development',
    ssl: false, // Explicitly disable SSL
    // ssl: configService.get('NODE_ENV') === 'production' ? { rejectUnauthorized: false } : false, // Original line
    retryAttempts: 3,
    retryDelay: 3000,
  };
  return dbOptions;
};

// For TypeORM CLI
const cliDataSourceOptions: DataSourceOptions = {
  type: 'postgres',
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT) || 5432,
  username: process.env.DB_USERNAME || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  database: process.env.DB_DATABASE || 'nellia_prospector',
  entities: [__dirname + '/../database/entities/*.entity{.ts,.js}'],
  migrations: [__dirname + '/../database/migrations/*{.ts,.js}'],
  synchronize: false, // Should be false for CLI usually
  logging: process.env.NODE_ENV === 'development',
  ssl: false, // Explicitly disable SSL for CLI DataSource
};

export const AppDataSource = new DataSource(cliDataSourceOptions);
