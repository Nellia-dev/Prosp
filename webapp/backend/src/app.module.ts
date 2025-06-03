import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ThrottlerModule } from '@nestjs/throttler';
import { BullModule } from '@nestjs/bull';

// Configuration
import { databaseConfig } from './config/database.config';
import { redisConfig } from './config/redis.config';

// Modules
import { AgentsModule } from './modules/agents/agents.module';
import { LeadsModule } from './modules/leads/leads.module';
import { BusinessContextModule } from './modules/business-context/business-context.module';
import { McpModule } from './modules/mcp/mcp.module';
import { ChatModule } from './modules/chat/chat.module';
import { MetricsModule } from './modules/metrics/metrics.module';
import { AuthModule } from './modules/auth/auth.module';
// TODO: Add these modules when implemented:
// import { AuthModule } from './modules/auth/auth.module';

@Module({
  imports: [
    // Configuration
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: ['.env.local', '.env'],
    }),

    // Database
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: databaseConfig,
      inject: [ConfigService],
    }),

    // Redis & Queue
    BullModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: redisConfig,
      inject: [ConfigService],
    }),

    // Rate limiting
    ThrottlerModule.forRoot([
      {
        ttl: 60000, // 1 minute
        limit: 100, // 100 requests per minute
      },
    ]),

    // Feature modules
    AgentsModule,
    LeadsModule,
    BusinessContextModule,
    McpModule,
    ChatModule,
    MetricsModule,
    AuthModule,
  ],
  controllers: [],
  providers: [],
})
export class AppModule {}
