#!/bin/bash

# ============================================
# Nellia Prospector - Development Environment Shutdown
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Nellia Prospector Development Environment...${NC}"
echo "============================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running.${NC}"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed or not in PATH.${NC}"
    exit 1
fi

# Stop and remove all services
echo -e "${BLUE}🐳 Stopping all Docker containers...${NC}"
docker-compose down

# Option to remove volumes (data persistence)
echo -e "\n${YELLOW}🗄️  Do you want to remove all data volumes? This will delete all database data. (y/N)${NC}"
read -t 10 -n 1 remove_volumes || remove_volumes="n"
echo ""

if [[ $remove_volumes =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️  Removing all volumes and data...${NC}"
    docker-compose down -v
    echo -e "${RED}🗑️  All data has been removed${NC}"
else
    echo -e "${GREEN}💾 Data volumes preserved${NC}"
fi

# Clean up any orphaned containers
echo -e "${BLUE}🧹 Cleaning up orphaned containers...${NC}"
docker-compose down --remove-orphans

# Option for complete cleanup
echo -e "\n${YELLOW}🧽 Do you want to remove unused Docker images and networks? (y/N)${NC}"
read -t 10 -n 1 cleanup_docker || cleanup_docker="n"
echo ""

if [[ $cleanup_docker =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🧹 Performing Docker system cleanup...${NC}"
    docker system prune -f
    echo -e "${GREEN}✅ Docker cleanup completed${NC}"
fi

# Final status check
echo -e "\n${BLUE}📊 Final Container Status:${NC}"
docker-compose ps

echo -e "\n${GREEN}✅ Nellia Prospector Development Environment stopped successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Quick commands:${NC}"
echo -e "  Start again:  ${GREEN}./start-dev.sh${NC}"
echo -e "  View logs:    ${GREEN}docker-compose logs [service-name]${NC}"
echo -e "  Remove all:   ${GREEN}docker-compose down -v --remove-orphans${NC}"
echo ""
echo -e "${YELLOW}💡 Your data is preserved unless you chose to remove volumes.${NC}"