# Nellia Prospector Development Environment
# Simple make commands to manage the development environment

.PHONY: dev start stop stop-clean setup install install-backend install-frontend install-python build build-backend build-frontend test test-backend test-frontend test-integration lint lint-backend lint-frontend logs logs-backend logs-frontend logs-db db-migrate db-reset db-reset-hard docker-up docker-down docker-reset health help prod-build prod-deploy prod-stop env-check admin monitoring security-check backup restore clean

# Default target
help:
	@echo "🚀 Nellia Prospector Development Commands"
	@echo ""
	@echo "🔧 Setup & Installation:"
	@echo "  make setup          - First-time setup (makes scripts executable and starts services)"
	@echo "  make install        - Install all dependencies"
	@echo "  make install-backend - Install backend dependencies"
	@echo "  make install-frontend - Install frontend dependencies"
	@echo "  make install-python - Install Python dependencies"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make dev           - Start all development services"
	@echo "  make start         - Start all development services (alias for dev)"
	@echo "  make stop          - Stop all services"
	@echo "  make stop-clean    - Stop all services and clean logs"
	@echo ""
	@echo "🏗️  Build:"
	@echo "  make build         - Build all components"
	@echo "  make build-backend - Build backend only"
	@echo "  make build-frontend - Build frontend only"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-backend  - Run backend tests"
	@echo "  make test-frontend - Run frontend tests"
	@echo "  make test-integration - Run full integration tests"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  make lint          - Lint all code"
	@echo "  make lint-backend  - Lint backend code"
	@echo "  make lint-frontend - Lint frontend code"
	@echo ""
	@echo "📊 Monitoring:"
	@echo "  make logs          - View all service logs"
	@echo "  make logs-backend  - View backend logs"
	@echo "  make logs-frontend - View frontend logs"
	@echo "  make logs-db       - View database logs"
	@echo "  make health        - Check API health"
	@echo ""
	@echo "🗄️  Database:"
	@echo "  make db-migrate    - Run database migrations"
	@echo "  make db-reset      - Reset database completely (keeps volumes)"
	@echo "  make db-reset-hard - Reset database and remove all data"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make docker-up     - Start Docker services"
	@echo "  make docker-down   - Stop Docker services"
	@echo "  make docker-reset  - Reset Docker services and volumes"
	@echo ""
	@echo "🚀 Production:"
	@echo "  make prod-build    - Build production images"
	@echo "  make prod-deploy   - Deploy to production"
	@echo "  make prod-stop     - Stop production services"
	@echo ""
	@echo "🛡️  Operations:"
	@echo "  make env-check     - Validate environment configuration"
	@echo "  make admin         - Start admin tools (PgAdmin, Redis Commander)"
	@echo "  make monitoring    - Start monitoring dashboard"
	@echo "  make security-check - Run security checks"
	@echo "  make backup        - Backup database and data"
	@echo "  make restore       - Restore from backup"
	@echo "  make clean         - Clean up Docker resources"

# Setup & Installation
setup:
	@echo "🔧 Setting up Nellia Prospector development environment..."
	chmod +x start-dev.sh stop-dev.sh
	./start-dev.sh

install: install-backend install-frontend install-python

install-backend:
	@echo "📦 Installing backend dependencies..."
	cd webapp/backend && npm install

install-frontend:
	@echo "📦 Installing frontend dependencies..."
	cd webapp/frontend && npm install

install-python:
	@echo "🐍 Setting up Python environment..."
	@if [ -d "python-project" ]; then \
		cd python-project && \
		python -m venv venv && \
		. venv/bin/activate && \
		pip install -r requirements.txt; \
	else \
		echo "⚠️  Python project directory not found, skipping..."; \
	fi

# Development
dev start:
	./start-dev.sh

stop:
	./stop-dev.sh

stop-clean:
	./stop-dev.sh --clean

# Build
build: build-backend build-frontend

build-backend:
	@echo "🏗️  Building backend..."
	cd webapp/backend && npm run build

build-frontend:
	@echo "🏗️  Building frontend..."
	cd webapp/frontend && npm run build

# Testing
test: test-backend test-frontend

test-backend:
	@echo "🧪 Running backend tests..."
	cd webapp/backend && npm test

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd webapp/frontend && npm test

# Code Quality
lint: lint-backend lint-frontend

lint-backend:
	@echo "🔍 Linting backend code..."
	cd webapp/backend && npm run lint

lint-frontend:
	@echo "🔍 Linting frontend code..."
	cd webapp/frontend && npm run lint

# Monitoring
logs:
	@echo "📊 Viewing all service logs..."
	tail -f logs/*.log

logs-backend:
	@echo "📊 Viewing backend logs..."
	tail -f logs/backend.log

logs-frontend:
	@echo "📊 Viewing frontend logs..."
	tail -f logs/frontend.log

logs-db:
	@echo "📊 Viewing database logs..."
	tail -f logs/postgres.log

health:
	@echo "🔍 Comprehensive health check..."
	@echo "Testing API health..."
	@curl -s http://localhost:3001/api/v1/health | jq . || echo "❌ Backend API not responding"
	@echo "Testing MCP Server..."
	@curl -s http://localhost:5001/health | jq . || echo "❌ MCP Server not responding"
	@echo "Testing Frontend..."
	@curl -s -o /dev/null -w "Status: %{http_code}" http://localhost:3000 || echo "❌ Frontend not responding"
	@echo ""
	@echo "Docker container status:"
	@docker-compose ps
	@echo ""
	@echo "🧪 Run full integration tests with: make test-integration"

test-integration:
	@echo "🧪 Running integration tests..."
	chmod +x integration-test.sh
	./integration-test.sh

# Database
db-migrate:
	@echo "🗄️  Running database migrations..."
	cd webapp/backend && npm run migration:run

db-reset:
	@echo "🗄️  Resetting database (soft reset - keeps volumes)..."
	@echo "Stopping services..."
	./stop-dev.sh
	@echo "Recreating database container..."
	docker-compose down postgres
	docker-compose up -d postgres
	@echo "Waiting for database to be ready..."
	@sleep 5
	@echo "Running migrations..."
	cd webapp/backend && npm run migration:run
	@echo "Database reset complete! Starting services..."
	./start-dev.sh

db-reset-hard:
	@echo "🗄️  Hard resetting database (removes all data)..."
	@echo "⚠️  This will permanently delete all database data!"
	@read -p "Are you sure? (y/N): " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Stopping services..."; \
		./stop-dev.sh; \
		echo "Removing database volumes..."; \
		docker-compose down -v; \
		echo "Starting fresh database..."; \
		docker-compose up -d postgres redis; \
		echo "Waiting for database to be ready..."; \
		sleep 10; \
		echo "Running migrations..."; \
		cd webapp/backend && npm run migration:run; \
		echo "Database hard reset complete! Starting services..."; \
		./start-dev.sh; \
	else \
		echo "Database reset cancelled."; \
	fi

# Docker
docker-up:
	@echo "🐳 Starting Docker services..."
	docker-compose up -d

docker-down:
	@echo "🐳 Stopping Docker services..."
	docker-compose down

docker-reset:
	@echo "🐳 Resetting Docker services..."
	docker-compose down -v
	docker-compose up -d

# Environment validation
env-check:
	@echo "🔍 Validating environment configuration..."
	@echo "Checking required files..."
	@test -f .env || (echo "❌ .env file not found. Run 'cp .env.example .env' and configure it." && exit 1)
	@test -f docker-compose.yml || (echo "❌ docker-compose.yml not found" && exit 1)
	@echo "✅ Required files present"
	@echo "Checking environment variables..."
	@if [ -z "$$OPENAI_API_KEY" ] || [ "$$OPENAI_API_KEY" = "your-openai-api-key-here" ]; then \
		echo "⚠️  OPENAI_API_KEY not configured properly"; \
	else \
		echo "✅ OPENAI_API_KEY configured"; \
	fi
	@if [ -z "$$JWT_SECRET" ] || [ "$$JWT_SECRET" = "your-super-secret-jwt-key-change-in-production" ]; then \
		echo "⚠️  JWT_SECRET should be changed for production"; \
	else \
		echo "✅ JWT_SECRET configured"; \
	fi
	@echo "✅ Environment validation complete"

# Production commands
prod-build:
	@echo "🏗️  Building production images..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file required for production build"; \
		exit 1; \
	fi
	docker-compose -f docker-compose.prod.yml build --no-cache
	@echo "✅ Production images built successfully"

prod-deploy:
	@echo "🚀 Deploying to production..."
	$(MAKE) env-check
	$(MAKE) prod-build
	@echo "Starting production services..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo "Waiting for services to be ready..."
	@sleep 30
	@echo "Running database migrations..."
	$(MAKE) db-migrate
	@echo "Running integration tests..."
	./integration-test.sh --quick
	@echo "✅ Production deployment complete!"
	@echo ""
	@echo "📊 Production services:"
	docker-compose -f docker-compose.prod.yml ps
	@echo ""
	@echo "🔍 Health check:"
	$(MAKE) health

prod-stop:
	@echo "🛑 Stopping production services..."
	docker-compose -f docker-compose.prod.yml down
	@echo "✅ Production services stopped"

# Admin tools
admin:
	@echo "🛠️  Starting admin tools..."
	docker-compose --profile admin up -d pgladmin redis-commander
	@echo "✅ Admin tools started"
	@echo ""
	@echo "🌐 Admin interfaces:"
	@echo "  PgAdmin:        http://localhost:5050 (admin@nellia.com/admin)"
	@echo "  Redis Commander: http://localhost:8081"

# Monitoring
monitoring:
	@echo "📊 Starting monitoring dashboard..."
	docker-compose --profile monitoring up -d monitoring
	@echo "✅ Monitoring started"
	@echo ""
	@echo "📊 Monitoring interface:"
	@echo "  Grafana: http://localhost:3002 (admin/admin)"

# Security checks
security-check:
	@echo "🛡️  Running security checks..."
	@echo "Checking for exposed secrets..."
	@if grep -r "password.*=" webapp/ --exclude-dir=node_modules --exclude="*.md" | grep -v "example" | grep -v "your-password-here"; then \
		echo "⚠️  Potential exposed passwords found"; \
	else \
		echo "✅ No exposed passwords found"; \
	fi
	@echo "Checking Docker security..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		-v $(PWD):/app \
		aquasec/trivy config /app/docker-compose.yml || echo "⚠️  Install Trivy for advanced security scanning"
	@echo "✅ Basic security check complete"

# Backup operations
backup:
	@echo "💾 Creating system backup..."
	@mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	@echo "Backing up database..."
	docker-compose exec -T postgres pg_dump -U postgres nellia_prospector > backups/$(shell date +%Y%m%d_%H%M%S)/database.sql
	@echo "Backing up volumes..."
	docker run --rm -v nellia-prospector_postgres_data:/data -v $(PWD)/backups/$(shell date +%Y%m%d_%H%M%S):/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
	docker run --rm -v nellia-prospector_redis_data:/data -v $(PWD)/backups/$(shell date +%Y%m%d_%H%M%S):/backup alpine tar czf /backup/redis_data.tar.gz -C /data .
	@echo "Backing up configuration..."
	@cp .env backups/$(shell date +%Y%m%d_%H%M%S)/env_backup
	@cp docker-compose.yml backups/$(shell date +%Y%m%d_%H%M%S)/
	@echo "✅ Backup created in backups/$(shell date +%Y%m%d_%H%M%S)/"

restore:
	@echo "🔄 Restoring from backup..."
	@echo "Available backups:"
	@ls -la backups/
	@echo "Enter backup directory name (YYYYMMDD_HHMMSS):"
	@read backup_dir && \
	if [ -d "backups/$$backup_dir" ]; then \
		echo "Stopping services..."; \
		docker-compose down; \
		echo "Restoring database..."; \
		docker-compose up -d postgres; \
		sleep 10; \
		docker-compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS nellia_prospector;"; \
		docker-compose exec -T postgres psql -U postgres -c "CREATE DATABASE nellia_prospector;"; \
		docker-compose exec -T postgres psql -U postgres nellia_prospector < "backups/$$backup_dir/database.sql"; \
		echo "Restoring volumes..."; \
		docker run --rm -v nellia-prospector_postgres_data:/data -v $(PWD)/backups/$$backup_dir:/backup alpine tar xzf /backup/postgres_data.tar.gz -C /data; \
		docker run --rm -v nellia-prospector_redis_data:/data -v $(PWD)/backups/$$backup_dir:/backup alpine tar xzf /backup/redis_data.tar.gz -C /data; \
		echo "✅ Restore complete"; \
		$(MAKE) dev; \
	else \
		echo "❌ Backup directory not found"; \
	fi

# Cleanup operations
clean:
	@echo "🧹 Cleaning up Docker resources..."
	@echo "Removing stopped containers..."
	docker container prune -f
	@echo "Removing unused images..."
	docker image prune -f
	@echo "Removing unused networks..."
	docker network prune -f
	@echo "Removing unused volumes..."
	@read -p "⚠️  Remove unused volumes? This may delete data! (y/N): " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker volume prune -f; \
	fi
	@echo "✅ Cleanup complete"