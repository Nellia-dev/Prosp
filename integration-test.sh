#!/bin/bash

# ============================================
# Nellia Prospector - Integration Test Script
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAX_WAIT_TIME=120
CHECK_INTERVAL=5

echo -e "${BLUE}🧪 Nellia Prospector Integration Test Suite${NC}"
echo "============================================"

# Function to check if a service is healthy
check_service_health() {
    local service_name=$1
    local health_url=$2
    local max_attempts=$((MAX_WAIT_TIME / CHECK_INTERVAL))
    local attempt=1

    echo -e "\n${YELLOW}⏳ Checking $service_name health...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is healthy${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - $service_name not ready yet...${NC}"
        sleep $CHECK_INTERVAL
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name health check failed after ${MAX_WAIT_TIME}s${NC}"
    return 1
}

# Function to test API endpoint
test_api_endpoint() {
    local endpoint_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -e "\n${YELLOW}🔍 Testing $endpoint_name...${NC}"
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$url")
    http_code=$(echo $response | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo $response | sed -e 's/HTTPSTATUS:.*//g')
    
    if [ "$http_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ $endpoint_name: HTTP $http_code${NC}"
        return 0
    else
        echo -e "${RED}❌ $endpoint_name: Expected HTTP $expected_status, got HTTP $http_code${NC}"
        echo -e "${RED}Response: $body${NC}"
        return 1
    fi
}

# Function to test WebSocket connection
test_websocket() {
    echo -e "\n${YELLOW}🔌 Testing WebSocket connection...${NC}"
    
    # Simple WebSocket test using curl (basic connectivity)
    if curl -s --include --no-buffer --header "Connection: Upgrade" --header "Upgrade: websocket" --header "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" --header "Sec-WebSocket-Version: 13" http://localhost:3001/socket.io/ | head -1 | grep -q "101"; then
        echo -e "${GREEN}✅ WebSocket connection available${NC}"
        return 0
    else
        echo -e "${RED}❌ WebSocket connection failed${NC}"
        return 1
    fi
}

# Function to test MCP integration
test_mcp_integration() {
    echo -e "\n${YELLOW}🤖 Testing MCP integration...${NC}"
    
    # Test backend MCP connection
    if test_api_endpoint "Backend MCP Health" "http://localhost:3001/api/v1/mcp/health"; then
        echo -e "${GREEN}✅ Backend MCP integration working${NC}"
    else
        echo -e "${RED}❌ Backend MCP integration failed${NC}"
        return 1
    fi
    
    # Test MCP agent status
    if test_api_endpoint "MCP Agent Status" "http://localhost:3001/api/v1/mcp/agents/all/status"; then
        echo -e "${GREEN}✅ MCP agent status endpoint working${NC}"
    else
        echo -e "${RED}❌ MCP agent status endpoint failed${NC}"
        return 1
    fi
    
    return 0
}

# Function to test database connectivity
test_database() {
    echo -e "\n${YELLOW}🗄️  Testing database connectivity...${NC}"
    
    # Test backend database health
    if test_api_endpoint "Backend Database Health" "http://localhost:3001/api/v1/health"; then
        echo -e "${GREEN}✅ Backend database connection working${NC}"
        return 0
    else
        echo -e "${RED}❌ Backend database connection failed${NC}"
        return 1
    fi
}

# Main test execution
main() {
    local failed_tests=0
    
    echo -e "\n${BLUE}📋 Starting integration tests...${NC}"
    
    # 1. Check service health
    echo -e "\n${BLUE}=== HEALTH CHECKS ===${NC}"
    
    check_service_health "PostgreSQL" "http://localhost:5432" || ((failed_tests++))
    check_service_health "Redis" "http://localhost:6379" || ((failed_tests++))
    check_service_health "MCP Server" "http://localhost:5001/health" || ((failed_tests++))
    check_service_health "Backend" "http://localhost:3001/api/v1/health" || ((failed_tests++))
    check_service_health "Frontend" "http://localhost:3000/health" || ((failed_tests++))
    
    # 2. Test API endpoints
    echo -e "\n${BLUE}=== API ENDPOINT TESTS ===${NC}"
    
    test_api_endpoint "Backend Health" "http://localhost:3001/api/v1/health" || ((failed_tests++))
    test_api_endpoint "Backend Swagger" "http://localhost:3001/api/docs" || ((failed_tests++))
    test_api_endpoint "MCP Server Health" "http://localhost:5001/health" || ((failed_tests++))
    test_api_endpoint "MCP Server Metrics" "http://localhost:5001/metrics" || ((failed_tests++))
    test_api_endpoint "Frontend" "http://localhost:3000" || ((failed_tests++))
    
    # 3. Test integrations
    echo -e "\n${BLUE}=== INTEGRATION TESTS ===${NC}"
    
    test_database || ((failed_tests++))
    test_mcp_integration || ((failed_tests++))
    test_websocket || ((failed_tests++))
    
    # 4. Test specific functionality
    echo -e "\n${BLUE}=== FUNCTIONALITY TESTS ===${NC}"
    
    test_api_endpoint "Agents List" "http://localhost:3001/api/v1/agents" || ((failed_tests++))
    test_api_endpoint "Leads List" "http://localhost:3001/api/v1/leads" || ((failed_tests++))
    test_api_endpoint "Metrics" "http://localhost:3001/api/v1/metrics" || ((failed_tests++))
    
    # Final results
    echo -e "\n${BLUE}=== TEST RESULTS ===${NC}"
    
    if [ $failed_tests -eq 0 ]; then
        echo -e "${GREEN}🎉 All integration tests passed!${NC}"
        echo -e "${GREEN}✅ System is ready for use${NC}"
        
        echo -e "\n${BLUE}📚 Available Services:${NC}"
        echo -e "Frontend:     ${YELLOW}http://localhost:3000${NC}"
        echo -e "Backend API:  ${YELLOW}http://localhost:3001/api/v1${NC}"
        echo -e "API Docs:     ${YELLOW}http://localhost:3001/api/docs${NC}"
        echo -e "MCP Server:   ${YELLOW}http://localhost:5001${NC}"
        echo -e "PgAdmin:      ${YELLOW}http://localhost:5050${NC} (if admin profile enabled)"
        echo -e "Redis Admin:  ${YELLOW}http://localhost:8081${NC} (if admin profile enabled)"
        
        return 0
    else
        echo -e "${RED}❌ $failed_tests integration test(s) failed${NC}"
        echo -e "${RED}⚠️  System may not be fully functional${NC}"
        
        echo -e "\n${YELLOW}🔧 Troubleshooting tips:${NC}"
        echo -e "1. Check Docker container logs: ${BLUE}docker-compose logs [service-name]${NC}"
        echo -e "2. Verify environment variables are set correctly"
        echo -e "3. Ensure all required ports are available"
        echo -e "4. Check if services have started completely"
        
        return 1
    fi
}

# Script options
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--quick] [--verbose]"
        echo "  --quick    Run only basic health checks"
        echo "  --verbose  Show detailed output"
        exit 0
        ;;
    --quick)
        echo -e "${BLUE}🚀 Quick health check mode${NC}"
        MAX_WAIT_TIME=30
        ;;
    --verbose)
        set -x
        ;;
esac

# Run main function
main
exit_code=$?

echo -e "\n${BLUE}Integration test completed with exit code: $exit_code${NC}"
exit $exit_code