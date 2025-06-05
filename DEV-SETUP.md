# Nellia Prospector - Development Setup Guide

Complete setup guide for running the Nellia Prospector application locally for development.

## 🚀 Quick Start

### One-Command Startup

```bash
# Make scripts executable (first time only)
chmod +x start-dev.sh stop-dev.sh

# Start all services
./start-dev.sh

# Stop all services
./stop-dev.sh

# Stop services and clean logs
./stop-dev.sh --clean
```

### Alternative: Using Make Commands

```bash
# First time setup
make setup

# Daily development
make dev        # Start all services
make stop       # Stop all services
make stop-clean # Stop and clean logs

# View all available commands
make help
```

### What Gets Started

The development environment includes:

- **🗄️ PostgreSQL** (port 5432) - Main database
- **🔄 Redis** (port 6379) - Queue and caching
- **🔧 NestJS Backend** (port 3001) - API server with WebSocket support
- **📱 Next.js Frontend** (port 3000) - React web application
- **🐍 Python Application** (port 8000) - AI agent processing (if exists)
- **🔌 MCP Server** (port 8080) - Model Context Protocol server (if exists)

## 📋 Prerequisites

### Required Software

- **Node.js** (v18+ recommended)
- **npm** or **yarn**
- **Python 3.8+** and **pip3**
- **Docker** and **Docker Compose**
- **Git**
- **Make** (optional, for convenience commands)

### Installation Commands

**macOS (with Homebrew):**
```bash
brew install node python docker docker-compose git make
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install nodejs npm python3 python3-pip docker.io docker-compose git make
```

**Windows:**
- Install Node.js from [nodejs.org](https://nodejs.org/)
- Install Python from [python.org](https://python.org/)
- Install Docker Desktop from [docker.com](https://docker.com/)
- Install Git from [git-scm.com](https://git-scm.com/)
- Install Make from [GnuWin32](http://gnuwin32.sourceforge.net/packages/make.htm) (optional)

## 🏗️ Project Structure

```
nellia-prospector/
├── start-dev.sh              # Development startup script
├── stop-dev.sh               # Development stop script
├── Makefile                  # Convenience commands
├── docker-compose.yml        # Database services
├── webapp/
│   ├── backend/              # NestJS API server
│   │   ├── src/
│   │   ├── package.json
│   │   └── .env (created automatically)
│   └── frontend/             # Next.js web app
│       ├── src/
│       ├── package.json
│       └── .env.local (created automatically)
├── python-project/           # Python AI agents (optional)
│   ├── main.py
│   ├── requirements.txt
│   └── venv/ (created automatically)
├── mcp-server/              # MCP protocol server (optional)
│   ├── src/
│   └── package.json
└── logs/                    # Service logs (created automatically)
    ├── frontend.log
    ├── backend.log
    ├── postgres.log
    ├── python.log
    └── mcp.log
```

## ⚙️ Development Commands

### Using Shell Scripts (Direct)

```bash
# Start all services
./start-dev.sh

# Stop all services
./stop-dev.sh

# Stop and clean logs
./stop-dev.sh --clean
```

### Using Make Commands (Recommended)

```bash
# Setup & Installation
make setup              # First-time setup
make install            # Install all dependencies
make install-backend    # Install backend dependencies only
make install-frontend   # Install frontend dependencies only
make install-python     # Install Python dependencies only

# Development
make dev               # Start all services
make stop              # Stop all services
make stop-clean        # Stop services and clean logs

# Building
make build             # Build all components
make build-backend     # Build backend only
make build-frontend    # Build frontend only

# Testing
make test              # Run all tests
make test-backend      # Run backend tests only
make test-frontend     # Run frontend tests only

# Code Quality
make lint              # Lint all code
make lint-backend      # Lint backend code only
make lint-frontend     # Lint frontend code only

# Monitoring
make logs              # View all service logs
make logs-backend      # View backend logs
make logs-frontend     # View frontend logs
make logs-db           # View database logs
make health            # Check API health

# Database
make db-migrate        # Run database migrations
make db-reset          # Reset database completely

# Docker
make docker-up         # Start Docker services only
make docker-down       # Stop Docker services only
make docker-reset      # Reset Docker services and volumes

# Help
make help              # Show all available commands
```

## ⚙️ Manual Setup (Alternative)

If you prefer to set up services manually:

### 1. Database Services

```bash
# Start databases
docker-compose up -d postgres redis

# Verify services
docker-compose ps
```

### 2. Backend Setup

```bash
cd webapp/backend

# Install dependencies
npm install

# Create environment file
cp .env.example .env  # Edit as needed

# Run migrations
npm run migration:run

# Start development server
npm run start:dev
```

### 3. Frontend Setup

```bash
cd webapp/frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env.local  # Edit as needed

# Start development server
npm run dev
```

### 4. Python Application (Optional)

```bash
cd python-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start application
python main.py
```

## 🔧 Configuration

### Environment Variables

The startup script automatically creates `.env` files with default development settings:

**Backend (.env):**
```env
NODE_ENV=development
PORT=3001
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_DATABASE=nellia_prospector
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_SECRET=dev-secret-key
GOOGLE_API_KEY=your-key-here
TAVILY_API_KEY=your-key-here
```

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:3001
NEXT_PUBLIC_WS_URL=ws://localhost:3001
NEXT_PUBLIC_ENVIRONMENT=development
```

### Database Configuration

- **Host:** localhost
- **Port:** 5432
- **Database:** nellia_prospector
- **Username:** postgres
- **Password:** postgres

## 📊 Monitoring & Debugging

### Service URLs

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:3001
- **API Documentation:** http://localhost:3001/api
- **Health Check:** http://localhost:3001/health
- **Python App:** http://localhost:8000 (if running)
- **MCP Server:** http://localhost:8080 (if running)

### Admin Interfaces (Optional)

Start admin interfaces with:
```bash
docker-compose --profile admin up -d
```

- **pgAdmin:** http://localhost:5050 (admin@nellia.com / admin)
- **Redis Commander:** http://localhost:8081

### Log Files

Real-time log monitoring:
```bash
# View all logs
make logs
# OR
tail -f logs/*.log

# Specific service logs
make logs-backend
make logs-frontend
make logs-db
```

### Debugging Commands

```bash
# Check service health
make health
# OR
curl http://localhost:3001/health

# List agents
curl http://localhost:3001/agents

# List leads
curl http://localhost:3001/leads

# Check database connection
docker exec nellia-postgres pg_isready -U postgres

# Check Redis connection
docker exec nellia-redis redis-cli ping
```

## 🔄 Development Workflow

### Daily Development

1. **Start services:** `make dev` or `./start-dev.sh`
2. **Develop:** Make changes to code
3. **Auto-reload:** Services automatically reload on file changes
4. **Test:** Use frontend at http://localhost:3000
5. **Stop services:** `make stop` or `./stop-dev.sh`

### Database Management

```bash
# Reset database (loses all data)
make db-reset

# Run specific migration
cd webapp/backend
npm run migration:run

# Create new migration
npm run migration:create -- CreateNewTable
```

### API Development

```bash
# Generate new module
cd webapp/backend
nest generate module feature-name
nest generate service feature-name
nest generate controller feature-name
```

## 🚨 Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Find process using port
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use stop script
make stop
```

**Database connection failed:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart database
docker-compose restart postgres
```

**Node modules issues:**
```bash
# Clean and reinstall
make install-backend
make install-frontend
```

**Python environment issues:**
```bash
# Recreate virtual environment
make install-python
```

### Service Status Check

```bash
# Check all ports
netstat -tulpn | grep -E ':(3000|3001|5432|6379|8000|8080)'

# Check Docker containers
docker ps

# Check Docker logs
docker-compose logs postgres
docker-compose logs redis
```

### Performance Issues

```bash
# Monitor resource usage
docker stats

# Check disk space
df -h

# Monitor system resources
top
```

## 🔒 Security Notes

**Development Environment Only:**
- Default passwords are used (postgres/postgres)
- JWT secret is a development key
- CORS is open for localhost
- Debug logging is enabled

**Never use these settings in production!**

## 📚 Additional Resources

- [NestJS Documentation](https://docs.nestjs.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Documentation](https://docs.docker.com/)
- [Make Documentation](https://www.gnu.org/software/make/manual/)

## 🆘 Getting Help

If you encounter issues:

1. Check the logs: `make logs`
2. Verify services are running: `docker ps`
3. Check ports: `netstat -tulpn | grep :300`
4. Restart services: `make stop && make dev`
5. Clean restart: `make stop-clean && make dev`

---

**Happy coding! 🚀**