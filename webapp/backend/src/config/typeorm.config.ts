import { DataSource, DataSourceOptions } from 'typeorm';
import { Agent } from '../database/entities/agent.entity';
import { Lead } from '../database/entities/lead.entity';
import { User } from '../database/entities/user.entity';
import { BusinessContextEntity } from '../database/entities/business-context.entity';
import { ChatMessage } from '../database/entities/chat-message.entity';

// Options for AppDataSource
const appDataSourceOptions: DataSourceOptions = {
  type: 'postgres' as const,
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT) || 5432,
  username: process.env.DB_USERNAME || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  database: process.env.DB_DATABASE || 'nellia_prospector',
  entities: [
    Agent,
    Lead,
    User,
    BusinessContextEntity,
    ChatMessage
  ],
  migrations: ['src/database/migrations/*.ts'],
  synchronize: false,
  logging: process.env.NODE_ENV === 'development',
  ssl: { // Attempt to enable SSL; for dev, might need rejectUnauthorized: false
    rejectUnauthorized: false, // INSECURE for production, use for local dev with self-signed certs
  }
};
console.log('APPDATASOURCE_CONSTRUCTION_OPTIONS:', JSON.stringify(appDataSourceOptions, null, 2));
export const AppDataSource = new DataSource(appDataSourceOptions);


// Configuration function for NestJS TypeOrmModule
// The return type here will be inferred by NestJS as TypeOrmModuleOptions
export const databaseConfig = (configService: any) => { // configService is typically ConfigService from @nestjs/config
  const dbOptions = {
    type: 'postgres' as const,
    host: configService.get('DB_HOST', 'localhost'), // No type arguments
    port: configService.get('DB_PORT', 5432),       // No type arguments
    username: configService.get('DB_USERNAME', 'postgres'), // No type arguments
    password: configService.get('DB_PASSWORD', 'postgres'), // No type arguments
    database: configService.get('DB_DATABASE', 'nellia_prospector'), // No type arguments
    entities: [
      Agent,
      Lead,
      User,
      BusinessContextEntity,
      ChatMessage
    ],
    migrations: ['dist/database/migrations/*.js'],
    synchronize: false,
    logging: configService.get('NODE_ENV') === 'development', // No type arguments
    ssl: { // Attempt to enable SSL; for dev, might need rejectUnauthorized: false
      rejectUnauthorized: false, // INSECURE for production, use for local dev with self-signed certs
    },
    // These are valid for TypeOrmModuleOptions, not strictly DataSourceOptions
    retryAttempts: 3,
    retryDelay: 3000,
  };
  console.log('DATABASE_CONFIG_OBJECT_FOR_TYPEORM_MODULE:', JSON.stringify(dbOptions, null, 2));
  return dbOptions;
};
