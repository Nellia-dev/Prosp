# Nellia Prospector Backend

A NestJS-based backend API that connects the React frontend with the Python MCP agent system for AI-powered B2B lead prospecting and processing.

## 🏗️ Architecture Overview

The backend serves as a bridge between:
- **Frontend**: React dashboard for user interaction
- **MCP Agent System**: Python-based AI agents for lead processing
- **Database**: PostgreSQL for persistent data storage
- **Queue System**: Redis/Bull for background job processing

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Docker (recommended) or PostgreSQL + Redis instances
- Python MCP server (for full functionality)

### Automated Setup

The easiest way to get started:

```bash
# Run the automated setup script
./scripts/setup-dev.sh
```

This script will:
- Check prerequisites
- Install dependencies
- Set up databases with Docker (if available)
- Create environment configuration
- Build the application

### Manual Setup

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start databases** (with Docker)
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

4. **Build and start**
   ```bash
   npm run build
   npm run start:dev
   ```

## 📁 Project Structure

```
src/
├── config/             # Configuration files
│   ├── database.config.ts
│   └── redis.config.ts
├── database/
│   ├── entities/       # TypeORM entities
│   └── migrations/     # Database migrations
├── modules/            # Feature modules
│   ├── agents/         # Agent management
│   ├── auth/           # Authentication (optional)
│   ├── business-context/ # Business configuration
│   ├── chat/           # Chat system
│   ├── leads/          # Lead management
│   ├── mcp/            # MCP server integration
│   └── metrics/        # Analytics & metrics
├── shared/
│   └── types/          # Shared TypeScript types
├── app.module.ts       # Root module
└── main.ts             # Application entry point
```

## 🔧 Core Modules

### Agents Module
- Manage AI agent lifecycle (start/stop/monitor)
- Agent metrics and performance tracking
- Integration with MCP server for agent control

### Leads Module
- CRUD operations for lead data
- Kanban board state management
- Lead processing workflow coordination
- Integration with MCP for AI processing

### MCP Module
- WebSocket communication with Python MCP server
- Request/response handling with timeout management
- Auto-reconnection with exponential backoff
- Health monitoring and status reporting

### Business Context Module
- Business configuration management
- Context synchronization with MCP agents
- Validation and persistence of business rules

### Chat Module
- Agent-user communication interface
- Message history and persistence
- Real-time chat coordination

### Metrics Module
- Performance analytics aggregation
- Dashboard data preparation
- Historical tracking and reporting

## 🛠️ API Documentation

Once running, visit the interactive API documentation:
- **Swagger UI**: `http://localhost:3001/api/docs`

### Key Endpoints

#### Agents
- `GET /api/agents` - List all agents
- `POST /api/agents/:id/start` - Start an agent
- `POST /api/agents/:id/stop` - Stop an agent
- `PUT /api/agents/:id/metrics` - Update agent metrics

#### Leads
- `GET /api/leads` - List leads with filtering
- `POST /api/leads` - Create new lead
- `PUT /api/leads/:id` - Update lead
- `GET /api/leads/kanban` - Get Kanban board data

#### MCP Integration
- `GET /api/mcp/health` - Check MCP server health
- `GET /api/mcp/status` - Get system status
- `POST /api/mcp/business-context` - Update business context

#### Metrics
- `GET /api/metrics/dashboard` - Get dashboard metrics
- `GET /api/metrics/performance` - Get performance data
- `GET /api/metrics/agents` - Get agent-specific metrics

## 🗃️ Database Schema

### Core Entities

#### Agents
- Agent identification and configuration
- Status tracking and metrics storage
- Task assignment and monitoring

#### Leads
- Company and contact information
- Processing stage tracking
- Scoring and qualification data
- Persona and analysis results

#### Business Context
- Business description and target market
- Value propositions and pain points
- Industry and geographic focus

#### Chat Messages
- Agent-user communication logs
- Message threading and history
- Attachment support

## 🔄 MCP Integration

The backend communicates with the Python MCP (Model Context Protocol) server via WebSocket:

### Connection Management
- Auto-connection on startup
- Heartbeat monitoring
- Exponential backoff reconnection
- Graceful degradation when MCP unavailable

### Message Types
- **Agent Control**: Start/stop/configure agents
- **Lead Processing**: Send leads for AI analysis
- **Business Context**: Sync configuration changes
- **Chat Messages**: Forward user communications

### Error Handling
- Timeout management for MCP requests
- Fallback responses when MCP unavailable
- Detailed error logging and monitoring

## 🚧 Development

### Available Commands

```bash
# Development
npm run start:dev          # Start with hot reload
npm run build              # Build for production
npm run start:prod         # Start production build

# Testing
npm run test               # Run unit tests
npm run test:e2e           # Run end-to-end tests
npm run test:cov           # Run tests with coverage

# Code Quality
npm run lint               # Run ESLint
npm run format             # Format with Prettier

# Database
npm run migration:generate # Generate new migration
npm run migration:run      # Run pending migrations
npm run migration:revert   # Revert last migration
```

### Database Commands (Docker)

```bash
# Start databases
docker-compose -f docker-compose.dev.yml up -d

# Stop databases
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Reset databases (⚠️ destroys data)
docker-compose -f docker-compose.dev.yml down -v
```

## 🔐 Environment Variables

Key configuration options in `.env`:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_DATABASE=nellia_prospector

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Application
NODE_ENV=development
PORT=3001
FRONTEND_URL=http://localhost:5173

# MCP Server
MCP_SERVER_URL=ws://localhost:8000/ws
MCP_SERVER_TIMEOUT=30000

# JWT (if auth enabled)
JWT_SECRET=your-secret-key
JWT_EXPIRES_IN=24h
```

## 📊 Monitoring & Health Checks

### Health Endpoints
- `GET /api/health` - Application health
- `GET /api/mcp/health` - MCP server connectivity
- `GET /api/mcp/status` - Detailed system status

### Metrics
- Response times and throughput
- Database connection health
- MCP server connectivity
- Agent processing performance

## 🚀 Deployment

### Production Checklist
- [ ] Set `NODE_ENV=production`
- [ ] Configure production database
- [ ] Set secure JWT secrets
- [ ] Enable SSL/TLS
- [ ] Configure CORS for production domain
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting
- [ ] Set up backup strategies

### Docker Deployment
```bash
# Build production image
docker build -t nellia-backend .

# Run with environment file
docker run --env-file .env -p 3001:3001 nellia-backend
```

## 🤝 Integration Points

### Frontend Integration
The backend provides REST APIs consumed by the React frontend:
- Real-time agent status updates
- Lead management and Kanban board data
- Chat message handling
- Business context configuration

### MCP Agent System Integration
WebSocket-based communication for:
- Agent lifecycle management
- Lead processing coordination
- Business context synchronization
- Chat message routing

## 📝 Development Status

Current completion: **~95%** (See [backend-todo.md](../backend-todo.md) for details)

### ✅ Completed
- All core modules implemented
- Database entities and relationships
- MCP integration with reconnection logic
- Comprehensive API endpoints
- Type definitions and validation
- Development tooling and scripts

### 🚧 Remaining
- Database migrations
- Production deployment configuration
- Comprehensive testing suite
- Performance optimization

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check if PostgreSQL is running
docker-compose -f docker-compose.dev.yml ps postgres

# View database logs
docker-compose -f docker-compose.dev.yml logs postgres
```

#### MCP Server Connection Issues
- Verify MCP server is running on configured URL
- Check WebSocket connectivity
- Review MCP server logs for errors

#### Build Failures
```bash
# Clean and reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check TypeScript compilation
npm run build
```

## 🔗 Related Documentation

- [Backend Todo List](../backend-todo.md) - Development roadmap
- [Frontend Documentation](../frontend/README.md) - React frontend
- [API Reference](http://localhost:3001/api/docs) - Interactive API docs

## 📄 License

This project is part of the Nellia Prospector system.
