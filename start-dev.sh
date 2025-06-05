#!/bin/bash

# ============================================
# Nellia Prospector - Development Environment Startup
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Nellia Prospector Development Environment...${NC}"
echo "============================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed or not in PATH.${NC}"
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env file with your API keys and configuration.${NC}"
    echo -e "${YELLOW}Important: Set your OPENAI_API_KEY and TAVILY_API_KEY${NC}"
    echo ""
    echo -e "${BLUE}Press Enter to continue once you've configured .env...${NC}"
    read
fi

# Load environment variables
if [ -f .env ]; then
    echo -e "${BLUE}📋 Loading environment variables...${NC}"
    set -a
    source .env
    set +a
fi

# Build and start services
echo -e "${BLUE}🐳 Building and starting Docker containers...${NC}"
docker-compose up -d --build

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to initialize...${NC}"
sleep 10

# Show service status
echo -e "\n${BLUE}📊 Service Status:${NC}"
docker-compose ps

# Check if integration test script should be run
echo -e "\n${BLUE}🧪 Would you like to run integration tests? (y/N)${NC}"
read -t 10 -n 1 run_tests || run_tests="n"
echo ""

if [[ $run_tests =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🧪 Running integration tests...${NC}"
    chmod +x integration-test.sh
    ./integration-test.sh --quick
else
    echo -e "${YELLOW}⏭️  Skipping integration tests${NC}"
fi

echo -e "\n${GREEN}✅ Development environment started!${NC}"
echo ""
echo -e "${BLUE}🌐 Available services:${NC}"
echo -e "  Frontend:     ${YELLOW}http://localhost:3000${NC}"
echo -e "  Backend API:  ${YELLOW}http://localhost:3001/api/v1${NC}"
echo -e "  API Docs:     ${YELLOW}http://localhost:3001/api/docs${NC}"
echo -e "  MCP Server:   ${YELLOW}http://localhost:5001${NC}"
echo -e "  Database:     ${YELLOW}localhost:5432${NC}"
echo -e "  Redis:        ${YELLOW}localhost:6379${NC}"
echo ""
echo -e "${BLUE}🛠️  Admin Tools (with admin profile):${NC}"
echo -e "  PgAdmin:      ${YELLOW}http://localhost:5050${NC} (admin@nellia.com/admin)"
echo -e "  Redis Cmd:    ${YELLOW}http://localhost:8081${NC}"
echo ""
echo -e "${BLUE}📋 Useful commands:${NC}"
echo -e "  Logs:         ${GREEN}docker-compose logs -f [service-name]${NC}"
echo -e "  Status:       ${GREEN}docker-compose ps${NC}"
echo -e "  Stop:         ${GREEN}./stop-dev.sh${NC}"
echo -e "  Integration:  ${GREEN}./integration-test.sh${NC}"
echo ""
echo -e "${BLUE}🔧 Admin tools profile:${NC}"
echo -e "  Start:        ${GREEN}docker-compose --profile admin up -d${NC}"
echo ""
echo -e "${YELLOW}💡 The system is now ready for development!${NC}"