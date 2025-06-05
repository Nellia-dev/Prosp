import { DataSource } from 'typeorm';
import { Agent } from '../database/entities/agent.entity';
import { Lead } from '../database/entities/lead.entity';
import { User } from '../database/entities/user.entity';
import { BusinessContextEntity } from '../database/entities/business-context.entity';
import { ChatMessage } from '../database/entities/chat-message.entity';

export const AppDataSource = new DataSource({
  type: 'postgres',
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
});

// Configuration function for NestJS TypeORM module
export const databaseConfig = (configService: any) => ({
  type: 'postgres' as const,
  host: configService.get('DB_HOST', 'localhost'),
  port: configService.get('DB_PORT', 5432),
  username: configService.get('DB_USERNAME', 'postgres'),
  password: configService.get('DB_PASSWORD', 'postgres'),
  database: configService.get('DB_DATABASE', 'nellia_prospector'),
  entities: [
    Agent,
    Lead,
    User,
    BusinessContextEntity,
    ChatMessage
  ],
  migrations: ['dist/database/migrations/*.js'],
  synchronize: false,
  logging: configService.get('NODE_ENV') === 'development',
  retryAttempts: 3,
  retryDelay: 3000,
});