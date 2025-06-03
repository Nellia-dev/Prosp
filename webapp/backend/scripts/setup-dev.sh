#!/bin/bash

# Nellia Prospector Backend - Development Setup Script
# This script helps set up the development environment

set -e

echo "🚀 Setting up Nellia Prospector Backend Development Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check prerequisites
echo -e "\n${BLUE}Checking prerequisites...${NC}"

if ! command_exists node; then
    print_error "Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

if ! command_exists npm; then
    print_error "npm is not installed. Please install npm."
    exit 1
fi

if ! command_exists docker; then
    print_warning "Docker is not installed. You'll need to set up PostgreSQL and Redis manually."
    DOCKER_AVAILABLE=false
else
    print_status "Docker is available"
    DOCKER_AVAILABLE=true
fi

if ! command_exists psql; then
    print_warning "PostgreSQL client is not installed. You won't be able to run direct database commands."
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_info "Creating .env file from .env.example..."
    cp .env.example .env
    print_status ".env file created"
else
    print_info ".env file already exists"
fi

# Install dependencies
echo -e "\n${BLUE}Installing dependencies...${NC}"
npm install
print_status "Dependencies installed"

# Setup databases with Docker if available
if [ "$DOCKER_AVAILABLE" = true ]; then
    echo -e "\n${BLUE}Setting up databases with Docker...${NC}"
    
    # Create docker-compose.yml for development
    cat > docker-compose.dev.yml << EOF
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: nellia-postgres
    environment:
      POSTGRES_DB: nellia_prospector
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: nellia-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
EOF

    print_status "docker-compose.dev.yml created"
    
    # Start the databases
    print_info "Starting PostgreSQL and Redis containers..."
    docker-compose -f docker-compose.dev.yml up -d
    
    # Wait for databases to be ready
    print_info "Waiting for databases to be ready..."
    sleep 10
    
    # Check if databases are running
    if docker-compose -f docker-compose.dev.yml ps postgres | grep -q "Up"; then
        print_status "PostgreSQL is running"
    else
        print_error "Failed to start PostgreSQL"
    fi
    
    if docker-compose -f docker-compose.dev.yml ps redis | grep -q "Up"; then
        print_status "Redis is running"
    else
        print_error "Failed to start Redis"
    fi
    
else
    echo -e "\n${YELLOW}Manual Database Setup Required${NC}"
    print_info "Please ensure you have PostgreSQL and Redis running:"
    print_info "  PostgreSQL: localhost:5432, database: nellia_prospector, user: postgres"
    print_info "  Redis: localhost:6379"
fi

# Build the application
echo -e "\n${BLUE}Building the application...${NC}"
npm run build
print_status "Application built successfully"

# Final instructions
echo -e "\n${GREEN}🎉 Development environment setup complete!${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
print_info "1. Review and update the .env file with your configuration"
print_info "2. Start the development server: npm run start:dev"
print_info "3. Visit the API documentation: http://localhost:3001/api/docs"

if [ "$DOCKER_AVAILABLE" = true ]; then
    print_info "4. Stop databases when done: docker-compose -f docker-compose.dev.yml down"
fi

print_info "5. Check the README.md for more development instructions"

echo -e "\n${BLUE}Development commands:${NC}"
echo "  npm run start:dev    - Start development server"
echo "  npm run build        - Build the application"
echo "  npm run test         - Run tests"
echo "  npm run lint         - Run linter"

if [ "$DOCKER_AVAILABLE" = true ]; then
    echo -e "\n${BLUE}Database commands:${NC}"
    echo "  docker-compose -f docker-compose.dev.yml up -d      - Start databases"
    echo "  docker-compose -f docker-compose.dev.yml down       - Stop databases"
    echo "  docker-compose -f docker-compose.dev.yml logs       - View logs"
fi

echo -e "\n${GREEN}Happy coding! 🚀${NC}"
