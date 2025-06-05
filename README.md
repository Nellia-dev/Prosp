# 🚀 Nellia Prospector - AI-Powered B2B Lead Processing System

> A robust, production-ready system with 4 interconnected services for intelligent lead analysis and processing.

## 🏗️ System Architecture

**4 Core Services Connected in Monolith Architecture:**

```
Frontend (React) ←→ Backend (NestJS) ←→ MCP Server (Flask) ←→ Prospect Agents (Python)
     3000                3001                  5001                Container
```

### Services Overview

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| **Frontend** | React 18 + TypeScript + Vite | 3000 | User interface, real-time monitoring |
| **Backend** | NestJS + PostgreSQL + Redis | 3001 | API server, business logic, data management |
| **MCP Server** | Flask + SQLAlchemy + SQLite | 5001 | Agent coordination, state tracking |
| **Prospect Agents** | Python + AI/LLM + AsyncIO | - | Lead processing, AI analysis |

## ✨ Key Features

- 🤖 **AI-Powered Lead Analysis** - Advanced LLM integration for intelligent lead processing
- 🔄 **Real-time Updates** - WebSocket connections for live system monitoring
- 📊 **Comprehensive Dashboard** - React-based UI with agent status and lead management
- 🔌 **MCP Integration** - Model Context Protocol for seamless agent coordination
- 🐳 **Containerized Architecture** - Docker Compose for easy deployment
- 🧪 **Robust Testing** - Integration tests validate all service connections
- 📈 **Production Ready** - Health checks, monitoring, and error handling

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### 1. Clone & Setup
```bash
git clone <repository-url>
cd nellia-prospector

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys (GOOGLE_API_KEY, TAVILY_API_KEY)
```

### 2. Start System
```bash
# Make scripts executable
chmod +x *.sh

# Validate configuration
./validate-connections.sh

# Start all services
./start-dev.sh
```

### 3. Verify & Test
```bash
# Run integration tests
./integration-test.sh

# Check service status
docker-compose ps
```

### 4. Access Services
- **🌐 Frontend**: http://localhost:3000
- **⚙️ Backend API**: http://localhost:3001/api/v1
- **📖 API Docs**: http://localhost:3001/api/docs
- **🔌 MCP Server**: http://localhost:5001

## 🔗 Service Connections

### Backend ↔ MCP Server Integration
- **HTTP Client**: `webapp/backend/src/modules/mcp/mcp.service.ts`
- **API Endpoints**: Health, agent status, lead processing
- **Configuration**: `MCP_SERVER_URL=http://prospect-mcp-server:5001`

### MCP Server ↔ Prospect Agents
- **Flask API**: `prospect/mcp-server/app.py`
- **Agent Coordination**: State tracking and event management
- **Database**: SQLite for persistent agent states

### Frontend ↔ Backend
- **REST API**: Full CRUD operations via `/api/v1/*`
- **WebSocket**: Real-time updates for agent status and lead processing
- **Authentication**: JWT-based security

## 🛠️ Development

### Project Structure
```
nellia-prospector/
├── webapp/
│   ├── frontend/          # React frontend
│   └── backend/           # NestJS backend
├── prospect/              # Python agents system
│   └── mcp-server/        # Flask MCP server
├── docker-compose.yml     # Service orchestration
├── start-dev.sh          # Development startup
├── stop-dev.sh           # Clean shutdown
└── integration-test.sh   # Connection validation
```

### Key Commands
```bash
# Development
./start-dev.sh              # Start all services
./stop-dev.sh               # Stop all services
./integration-test.sh       # Test all connections
./validate-connections.sh   # Validate configuration

# Docker operations
docker-compose ps           # Service status
docker-compose logs -f      # View logs
docker-compose down -v      # Remove with data
```

### Admin Tools (Optional)
```bash
# Start with admin interfaces
docker-compose --profile admin up -d

# Access admin tools
# PgAdmin: http://localhost:5050 (admin@nellia.com/admin)
# Redis Commander: http://localhost:8081
```

## 🧪 Testing & Validation

### Static Validation
- ✅ File structure and configuration
- ✅ Docker setup and dependencies
- ✅ Environment variables
- ✅ Service definitions

### Runtime Testing
- ✅ Service health checks
- ✅ API endpoint validation
- ✅ Database connectivity
- ✅ MCP integration
- ✅ WebSocket connections

### Integration Scenarios
- ✅ End-to-end lead processing
- ✅ Agent coordination workflows
- ✅ Real-time status updates
- ✅ Error handling and recovery

## 📊 Monitoring & Observability

### Health Endpoints
- Backend: `/api/v1/health`
- MCP Server: `/health`
- Frontend: `/health`

### Logging
```bash
# Service-specific logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f prospect-mcp-server
docker-compose logs -f prospect-agents

# All logs
docker-compose logs -f
```

### Metrics
- System metrics via `/api/v1/metrics`
- Agent performance tracking
- Lead processing statistics
- Real-time dashboard updates

## 🔒 Security

- **Container Security**: Non-root users, security headers
- **Authentication**: JWT-based API security
- **Network Security**: Internal service communication
- **Environment**: Secure configuration management
- **CORS**: Proper cross-origin configuration

## 📈 Production Deployment

### Environment Configuration
```bash
# Production settings in .env
NODE_ENV=production
DB_HOST=your-production-db
REDIS_HOST=your-production-redis
MCP_SERVER_URL=https://your-mcp-server
```

### Scaling Options
- **Backend**: Horizontal scaling with load balancer
- **MCP Server**: Multiple instances for high availability
- **Database**: PostgreSQL clustering
- **Caching**: Redis cluster mode

## 🤝 Contributing

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Test** your changes (`./integration-test.sh`)
4. **Commit** changes (`git commit -m 'Add amazing feature'`)
5. **Push** to branch (`git push origin feature/amazing-feature`)
6. **Open** Pull Request

## 📚 Documentation

- **[System Architecture](SYSTEM_ARCHITECTURE.md)** - Detailed architecture overview
- **[Connection Summary](CONNECTION_SUMMARY.md)** - Service integration details
- **[Development Setup](DEV-SETUP.md)** - Development environment guide
- **[Production Roadmap](PRODUCTION_ROADMAP.md)** - Production deployment guide

## 🆘 Troubleshooting

### Common Issues
```bash
# Port conflicts
./stop-dev.sh && ./start-dev.sh

# Permission issues
chmod +x *.sh

# Docker issues
docker-compose down -v
docker system prune -f

# Service logs
docker-compose logs -f [service-name]
```

### Support
- Check integration tests: `./integration-test.sh`
- Validate configuration: `./validate-connections.sh`
- Review logs for specific services
- Ensure API keys are properly configured

## 🎉 Success Metrics

**✅ All Systems Connected and Operational:**
- 4 services running in harmony
- Real-time data flow between components
- Comprehensive error handling
- Production-ready architecture
- Extensive testing coverage

---

**🚀 The Nellia Prospector is ready for intelligent B2B lead processing!**

Built with ❤️ using modern technologies and best practices.
