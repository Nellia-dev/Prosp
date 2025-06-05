#!/bin/bash

# ============================================
# Nellia Prospector - Production Deployment Script
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Nellia Prospector Production Deployment${NC}"
echo "============================================"

# Check if running as production
if [ "$NODE_ENV" != "production" ]; then
    echo -e "${YELLOW}⚠️  NODE_ENV is not set to 'production'. Continue? (y/N)${NC}"
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Deployment cancelled${NC}"
        exit 1
    fi
fi

# Pre-deployment checks
echo -e "${BLUE}🔍 Running pre-deployment checks...${NC}"

# Check if production env file exists
if [ ! -f .env.production ]; then
    echo -e "${RED}❌ .env.production file not found${NC}"
    echo -e "${YELLOW}💡 Copy .env.production template and configure it${NC}"
    exit 1
fi

# Check if required commands exist
for cmd in docker docker-compose jq curl; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}❌ $cmd is not installed${NC}"
        exit 1
    fi
done

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Pre-deployment checks passed${NC}"

# Backup current production (if exists)
echo -e "${BLUE}💾 Creating backup before deployment...${NC}"
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    make backup
    echo -e "${GREEN}✅ Backup completed${NC}"
else
    echo -e "${YELLOW}⏭️  No existing production deployment found, skipping backup${NC}"
fi

# Load production environment
echo -e "${BLUE}📋 Loading production environment...${NC}"
set -a
source .env.production
set +a

# Validate critical environment variables
echo -e "${BLUE}🔒 Validating environment configuration...${NC}"
required_vars=("DB_PASSWORD" "JWT_SECRET" "OPENAI_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ] || [[ "${!var}" == *"your-"* ]]; then
        echo -e "${RED}❌ $var is not properly configured${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ Environment validation passed${NC}"

# Deploy to production
echo -e "${BLUE}🚀 Starting production deployment...${NC}"

# Stop existing production services
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo -e "${YELLOW}🛑 Stopping existing production services...${NC}"
    docker-compose -f docker-compose.prod.yml down
fi

# Build production images
echo -e "${BLUE}🏗️  Building production images...${NC}"
docker-compose -f docker-compose.prod.yml build --no-cache

# Start production services
echo -e "${BLUE}🐳 Starting production services...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to initialize...${NC}"
sleep 30

# Run database migrations
echo -e "${BLUE}🗄️  Running database migrations...${NC}"
make db-migrate

# Health check
echo -e "${BLUE}🔍 Running health checks...${NC}"
max_attempts=12
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f -s http://localhost:3001/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is healthy${NC}"
        break
    fi
    
    echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - waiting for backend...${NC}"
    sleep 10
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo -e "${RED}Deployment may have issues${NC}"
    exit 1
fi

# Run integration tests
echo -e "${BLUE}🧪 Running integration tests...${NC}"
if ./integration-test.sh --quick; then
    echo -e "${GREEN}✅ Integration tests passed${NC}"
else
    echo -e "${RED}❌ Integration tests failed${NC}"
    echo -e "${YELLOW}⚠️  Check logs for issues${NC}"
fi

# Final status
echo -e "\n${GREEN}🎉 Production deployment completed!${NC}"
echo ""
echo -e "${BLUE}📊 Production Status:${NC}"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo -e "${BLUE}🌐 Production Services:${NC}"
echo -e "  Frontend:     ${YELLOW}http://localhost:3000${NC}"
echo -e "  Backend API:  ${YELLOW}http://localhost:3001/api/v1${NC}"
echo -e "  API Docs:     ${YELLOW}http://localhost:3001/api/docs${NC}"

echo ""
echo -e "${BLUE}📋 Useful Commands:${NC}"
echo -e "  Status:       ${GREEN}docker-compose -f docker-compose.prod.yml ps${NC}"
echo -e "  Logs:         ${GREEN}docker-compose -f docker-compose.prod.yml logs -f${NC}"
echo -e "  Stop:         ${GREEN}make prod-stop${NC}"
echo -e "  Backup:       ${GREEN}make backup${NC}"

echo ""
echo -e "${YELLOW}💡 Production deployment is now live!${NC}"