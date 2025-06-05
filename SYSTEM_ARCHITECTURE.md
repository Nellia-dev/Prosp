# Nellia Prospector - System Architecture

## Overview
The Nellia Prospector is a robust AI-powered B2B lead processing system with 4 main services running in a monolith architecture, all properly connected and orchestrated.

## 🏗️ Architecture Components

### 1. Frontend (React/Vite)
- **Location**: `webapp/frontend/`
- **Port**: 3000
- **Technology**: React 18, TypeScript, Vite, Tailwind CSS
- **Purpose**: User interface for managing leads, agents, and monitoring system
- **Docker**: Multi-stage build with Nginx production server
- **Health Check**: `/health` endpoint

### 2. Backend (NestJS)
- **Location**: `webapp/backend/`
- **Port**: 3001
- **Technology**: NestJS, TypeScript, PostgreSQL, Redis, Bull Queue
- **Purpose**: API server, business logic, data management
- **Docker**: Multi-stage build with Node.js
- **Health Check**: `/api/v1/health` endpoint

### 3. Prospect Agents System (Python)
- **Location**: `prospect/`
- **Technology**: Python 3.12, Pydantic, LLM clients, AsyncIO
- **Purpose**: AI agent orchestration and lead processing
- **Main Entry**: `enhanced_main.py`
- **Docker**: Python-based with Playwright support

### 4. MCP Server (Flask)
- **Location**: `prospect/mcp-server/`
- **Port**: 5001
- **Technology**: Flask, SQLAlchemy, SQLite
- **Purpose**: Model Context Protocol server for agent coordination
- **Docker**: Gunicorn WSGI server
- **Health Check**: `/health` endpoint

## 🔗 Service Connections

### Connection Flow
```
Frontend (3000) 
    ↓ HTTP/WebSocket
Backend (3001)
    ↓ HTTP API
MCP Server (5001)
    ↓ Internal Communication
Prospect Agents System
```

### Key Integration Points

1. **Frontend ↔ Backend**
   - REST API calls via `/api/v1/*`
   - WebSocket connection for real-time updates
   - Authentication via JWT tokens

2. **Backend ↔ MCP Server**
   - HTTP client in `McpService` (`webapp/backend/src/modules/mcp/mcp.service.ts`)
   - Endpoints: health, agent status, lead processing, metrics
   - Configuration: `MCP_SERVER_URL=http://prospect-mcp-server:5001`

3. **MCP Server ↔ Prospect Agents**
   - Flask API endpoints for agent coordination
   - SQLite database for tracking lead processing states
   - Agent event recording and status management

4. **Database Connections**
   - PostgreSQL for backend persistent data
   - Redis for caching and queue management
   - SQLite for MCP server tracking

## 🐳 Docker Architecture

### Services in docker-compose.yml
```yaml
services:
  postgres:          # Database
  redis:             # Cache & Queue
  prospect-mcp-server:   # MCP Server (Flask)
  prospect-agents:       # Agents System (Python)
  backend:               # API Server (NestJS)
  frontend:              # Web UI (React/Nginx)
```

### Networks
- Custom bridge network: `nellia-network`
- Subnet: `172.20.0.0/16`
- All services communicate via service names

### Volumes
- `postgres_data`: Database persistence
- `redis_data`: Redis persistence
- `mcp_server_data`: MCP tracking data
- `prospect_data`: Agent processing data
- `backend_uploads`: File uploads

## 🔧 Configuration

### Environment Variables
```bash
# Database
DB_HOST=postgres
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=postgres

# MCP Integration
MCP_SERVER_URL=http://prospect-mcp-server:5001
ENABLE_MCP_REPORTING=true

# AI Services
GOOGLE_API_KEY=your-key
TAVILY_API_KEY=your-key
```

### Health Checks
- All services have health check endpoints
- Docker health checks with retry logic
- Integration test script validates all connections

## 🚀 Deployment

### Development
```bash
# Start all services
./start-dev.sh

# Stop all services
./stop-dev.sh

# Run integration tests
./integration-test.sh
```

### Production
```bash
# Start with production configuration
docker-compose up -d

# Start with admin tools
docker-compose --profile admin up -d

# Start with monitoring
docker-compose --profile monitoring up -d
```

## 📊 Monitoring & Observability

### Available Endpoints
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:3001/api/v1`
- API Documentation: `http://localhost:3001/api/docs`
- MCP Server: `http://localhost:5001`
- Health Checks: All services have `/health`

### Admin Tools (Optional)
- PgAdmin: `http://localhost:5050`
- Redis Commander: `http://localhost:8081`
- Grafana: `http://localhost:3002` (monitoring profile)

### Logging
- Container logs: `docker-compose logs -f [service]`
- Structured logging in all services
- Error tracking and metrics collection

## 🔒 Security

### Production Security
- Non-root users in containers
- Security headers in Nginx
- JWT authentication
- CORS configuration
- Environment variable separation

### Network Security
- Internal service communication
- No direct external access to databases
- Proper port exposure configuration

## 🧪 Testing

### Integration Tests
- Service health verification
- API endpoint testing
- Database connectivity
- MCP integration validation
- WebSocket connection testing

### Test Execution
```bash
# Quick health check
./integration-test.sh --quick

# Full integration test suite
./integration-test.sh

# Verbose output
./integration-test.sh --verbose
```

## 📈 Scalability

### Horizontal Scaling
- Backend can be scaled with load balancer
- MCP server can handle multiple agent instances
- Database clustering supported
- Redis cluster mode available

### Performance Optimization
- Nginx for static file serving
- Redis caching layer
- Database connection pooling
- Queue-based processing

## 🔄 Data Flow

### Lead Processing Pipeline
1. **Input**: Lead data via API or file upload
2. **Validation**: Backend validates and stores lead
3. **Queue**: Lead queued for processing
4. **MCP Coordination**: MCP server tracks processing state
5. **Agent Processing**: Python agents process lead
6. **Results**: Processed data returned to backend
7. **Frontend Update**: Real-time updates via WebSocket

### Agent Communication
1. **Start Processing**: Backend notifies MCP server
2. **Agent Execution**: Agents report progress to MCP
3. **Status Updates**: MCP tracks agent states
4. **Completion**: Final results aggregated
5. **Notification**: Backend receives completion event

## 🛠️ Development Workflow

### Local Development
1. Copy `.env.example` to `.env`
2. Set API keys and configuration
3. Run `./start-dev.sh`
4. All services start automatically
5. Integration tests validate setup

### Code Changes
- Frontend: Hot reload enabled
- Backend: Watch mode with auto-restart
- Agents: Manual restart required
- MCP: Gunicorn auto-reload in dev mode

This architecture ensures all services are properly connected, with clear separation of concerns and robust error handling throughout the system.