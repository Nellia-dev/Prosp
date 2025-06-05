# Database Setup Guide

This guide explains how to set up and manage the database for the Nellia Prospector backend.

## Prerequisites

- PostgreSQL 12+ installed and running
- Node.js 18+ installed
- All backend dependencies installed (`npm install`)

## Environment Variables

Ensure these environment variables are set in your `.env` file:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_DATABASE=nellia_prospector
NODE_ENV=development
```

## Database Entities

The system includes the following main entities:

### 1. Users (`users`)
- User authentication and authorization
- Admin and regular user roles
- Email-based authentication

### 2. Agents (`agents`)
- AI agents for lead processing
- 25 different agent types across 4 categories:
  - **Initial Processing**: `lead_intake_agent`, `lead_analysis_agent`
  - **Orchestrator**: `enhanced_lead_processor`
  - **Specialized**: 15 specialized agents for different tasks
  - **Alternative**: 7 alternative/modular agents
- Real-time metrics and status tracking

### 3. Leads (`leads`)
- Lead data and processing information
- Scoring metrics (relevance, ROI potential, Brazilian market fit)
- Processing stages and qualification tiers
- Contact information and analysis results

### 4. Business Context (`business_context`)
- Company business information
- Target market and value proposition
- Industry focus and geographic targeting

### 5. Chat Messages (`chat_messages`)
- Agent-user communication
- File attachment support
- Message history and timestamps

## Entity Relationships

```
Users ←→ [General system access]
Agents ←→ ChatMessages (One-to-Many)
Leads [Independent processing pipeline]
BusinessContext [System configuration]
```

## Running Migrations

### 1. Run All Migrations
```bash
npm run migration:run
```

### 2. Check Migration Status
```bash
npm run migration:show
```

### 3. Revert Last Migration (if needed)
```bash
npm run migration:revert
```

### 4. Generate New Migration (for schema changes)
```bash
npm run migration:generate
```

## Development vs Production

- **Development**: `synchronize: true` - TypeORM auto-syncs schema changes
- **Production**: `synchronize: false` - Only run explicit migrations

## Initial Data

The system includes seed data for:
- All 25 AI agents with default metrics
- Proper agent categorization
- Initial status settings

## Database Schema Features

- **UUID Primary Keys**: All entities use UUID for better distribution
- **Enum Types**: Proper PostgreSQL enums for type safety
- **JSONB Support**: Complex data structures (metrics, persona data)
- **Array Support**: String arrays for lists (pain points, triggers)
- **Timestamps**: Automatic created/updated tracking
- **Constraints**: Foreign keys and unique constraints

## Troubleshooting

### Migration Issues
- Ensure database exists and is accessible
- Check environment variables
- Verify PostgreSQL is running
- Check migration file syntax

### Schema Sync Issues
- In development, drop and recreate database if needed
- Ensure all entities are properly imported
- Check for enum definition conflicts

### Performance
- Indexes are automatically created for primary keys and foreign keys
- Consider adding indexes for frequently queried fields
- Monitor query performance in production

## Backup and Recovery

### Development Backup
```bash
pg_dump -h localhost -U postgres nellia_prospector > backup.sql
```

### Restore from Backup
```bash
psql -h localhost -U postgres nellia_prospector < backup.sql