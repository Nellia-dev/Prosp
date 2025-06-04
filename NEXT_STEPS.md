# Nellia Prospector Platform - Next Steps Implementation Guide

## 🚀 **Immediate Next Steps (Implementation Priority)**

### 1. **Setup and Test Core Integration** (High Priority)

#### MCP Server Setup
```bash
# Initialize and start MCP Server
cd prospect/mcp-server
python -c "from database import init_db; init_db()"
python app.py
```

#### Test Prospect Core with MCP Integration
```bash
# Test Prospect Core with MCP reporting enabled
cd prospect
ENABLE_MCP_REPORTING=true python enhanced_main.py leads.json -p "Test product"
```

#### Backend Integration Test
```bash
# Install dependencies and start backend
cd webapp/backend
npm install
npm run start:dev
```

#### Frontend Integration Test
```bash
# Start frontend development server
cd webapp/frontend
npm install
npm run dev
```

### 2. **Configure Environment Variables** (High Priority)

#### Prospect Core Environment (prospect/.env)
```env
# Core LLM Configuration
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# MCP Server Integration
ENABLE_MCP_REPORTING=true
MCP_SERVER_URL=http://localhost:5001

# Processing Configuration
ENABLE_ENHANCED_PROCESSING=true
MAX_LEADS_PER_BATCH=100
```

#### Backend Environment (webapp/backend/.env)
```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/nellia_db
REDIS_URL=redis://localhost:6379

# MCP Server Integration
MCP_SERVER_URL=http://localhost:5001
MCP_SERVER_TIMEOUT=30000

# JWT Configuration
JWT_SECRET=your_jwt_secret_here
JWT_EXPIRES_IN=24h

# API Keys
OPENAI_API_KEY=your_openai_key_here
```

#### Frontend Environment (webapp/frontend/.env)
```env
# Backend API Configuration
VITE_API_BASE_URL=http://localhost:3000
VITE_WS_URL=ws://localhost:3000

# Application Configuration
VITE_APP_NAME=Nellia Prospector
VITE_APP_VERSION=1.0.0
```

### 3. **Test End-to-End Workflow** (High Priority)

#### Complete Integration Test Script
```bash
#!/bin/bash
# save as test_integration.sh

echo "🚀 Starting Nellia Prospector Integration Test..."

# 1. Start MCP Server
echo "📊 Starting MCP Server..."
cd prospect/mcp-server
python app.py &
MCP_PID=$!
sleep 5

# 2. Start Backend
echo "🔧 Starting Backend..."
cd ../../webapp/backend
npm run start:dev &
BACKEND_PID=$!
sleep 10

# 3. Start Frontend  
echo "🎨 Starting Frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
sleep 5

# 4. Test Processing
echo "🧠 Testing Lead Processing..."
cd ../../prospect
python enhanced_main.py leads.json -p "AI automation tools" --limit 5

# 5. Test API Endpoints
echo "🔍 Testing API Endpoints..."
curl -s http://localhost:5001/health
curl -s http://localhost:3000/api/health

echo "✅ Integration test completed!"
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend: http://localhost:3000"
echo "📊 MCP Server: http://localhost:5001"

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up processes..."
    kill $MCP_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
}
trap cleanup EXIT
```

## 🔧 **Development Tasks (Medium Priority)**

### 4. **Enhance MCP Server Integration**

#### Add Health Check Endpoints
```python
# Add to prospect/mcp-server/app.py

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "version": "1.0.0"
    })

@app.route('/metrics', methods=['GET'])
def get_metrics():
    db: Session = next(database.get_db())
    try:
        total_leads = db.query(models.LeadProcessingStateOrm).count()
        active_leads = db.query(models.LeadProcessingStateOrm).filter(
            models.LeadProcessingStateOrm.status == LeadProcessingStatusEnum.ACTIVE
        ).count()
        
        return jsonify({
            "total_leads": total_leads,
            "active_leads": active_leads,
            "database_size": "N/A"  # Add actual DB size calculation
        })
    finally:
        db.close()
```

### 5. **Frontend Integration Completion**

#### Real-time MCP Data Integration
```typescript
// Create webapp/frontend/src/hooks/useMCPData.ts

import { useState, useEffect } from 'react';
import { api } from '../services/api';

export interface MCPMetrics {
  totalLeads: number;
  activeLeads: number;
  completedLeads: number;
  failedLeads: number;
}

export const useMCPData = () => {
  const [metrics, setMetrics] = useState<MCPMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await api.get('/mcp/metrics');
        setMetrics(response.data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch MCP metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  return { metrics, loading, error };
};
```

### 6. **Backend API Enhancement**

#### Add MCP Data Endpoints
```typescript
// Add to webapp/backend/src/modules/mcp/mcp.controller.ts

import { Controller, Get, Param } from '@nestjs/common';
import { McpService } from './mcp.service';

@Controller('mcp')
export class McpController {
  constructor(private readonly mcpService: McpService) {}

  @Get('health')
  async getHealth() {
    return await this.mcpService.getHealth();
  }

  @Get('metrics')
  async getMetrics() {
    return await this.mcpService.getMetrics();
  }

  @Get('leads/:leadId/status')
  async getLeadStatus(@Param('leadId') leadId: string) {
    return await this.mcpService.getLeadStatus(leadId);
  }

  @Get('runs/:runId/status')
  async getRunStatus(@Param('runId') runId: string) {
    return await this.mcpService.getRunStatus(runId);
  }
}
```

## 📊 **Quality Assurance (Medium Priority)**

### 7. **Testing & Validation**

#### Automated Test Suite
```bash
# Create comprehensive test script
# save as run_all_tests.sh

#!/bin/bash
echo "🧪 Running Nellia Prospector Test Suite..."

# Test Prospect Core
echo "📊 Testing Prospect Core..."
cd prospect
python tests/test_runner.py --type all
PROSPECT_EXIT_CODE=$?

# Test Backend
echo "🔧 Testing Backend..."
cd ../webapp/backend
npm run test
npm run test:e2e
BACKEND_EXIT_CODE=$?

# Test Frontend
echo "🎨 Testing Frontend..."
cd ../frontend
npm run test
FRONTEND_EXIT_CODE=$?

# Generate test report
echo "📋 Test Results Summary:"
echo "Prospect Core: $([ $PROSPECT_EXIT_CODE -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
echo "Backend: $([ $BACKEND_EXIT_CODE -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"
echo "Frontend: $([ $FRONTEND_EXIT_CODE -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")"

# Exit with error if any tests failed
[ $PROSPECT_EXIT_CODE -eq 0 ] && [ $BACKEND_EXIT_CODE -eq 0 ] && [ $FRONTEND_EXIT_CODE -eq 0 ]
```

### 8. **Performance Optimization**

#### Load Testing Configuration
```javascript
// Create load_test.js for testing with k6 or similar

import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 10 }, // Ramp up
    { duration: '5m', target: 10 }, // Stay at 10 users
    { duration: '2m', target: 0 },  // Ramp down
  ],
};

export default function () {
  // Test MCP Server
  let mcpResponse = http.get('http://localhost:5001/health');
  check(mcpResponse, {
    'MCP server status is 200': (r) => r.status === 200,
  });

  // Test Backend API
  let backendResponse = http.get('http://localhost:3000/api/health');
  check(backendResponse, {
    'Backend status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
```

## 🚀 **Production Readiness (Low Priority)**

### 9. **Deployment Preparation**

#### Docker Configuration
```yaml
# Create docker-compose.yml

version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: nellia_db
      POSTGRES_USER: nellia_user
      POSTGRES_PASSWORD: nellia_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  mcp-server:
    build: ./prospect/mcp-server
    ports:
      - "5001:5001"
    depends_on:
      - postgres
    environment:
      - DATABASE_URL=postgresql://nellia_user:nellia_password@postgres:5432/nellia_db

  backend:
    build: ./webapp/backend
    ports:
      - "3000:3000"
    depends_on:
      - postgres
      - redis
      - mcp-server
    environment:
      - DATABASE_URL=postgresql://nellia_user:nellia_password@postgres:5432/nellia_db
      - REDIS_URL=redis://redis:6379
      - MCP_SERVER_URL=http://mcp-server:5001

  frontend:
    build: ./webapp/frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    environment:
      - VITE_API_BASE_URL=http://backend:3000

volumes:
  postgres_data:
```

### 10. **Monitoring & Logging**

#### Centralized Logging Configuration
```yaml
# Create logging-stack.yml

version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    depends_on:
      - elasticsearch
```

## 🎯 **Recommended Implementation Order**

### Phase 1: Core Integration (Week 1)
1. Setup MCP Server and test basic functionality
2. Configure all environment variables
3. Test end-to-end workflow
4. Verify data flow between components

### Phase 2: Enhancement (Week 2)
1. Add health checks and monitoring
2. Complete frontend integration
3. Enhance backend API endpoints
4. Implement error handling

### Phase 3: Quality & Testing (Week 3)
1. Run comprehensive test suites
2. Performance optimization
3. Load testing
4. Security validation

### Phase 4: Production Prep (Week 4)
1. Docker containerization
2. CI/CD pipeline setup
3. Monitoring and logging
4. Documentation finalization

## 🔍 **Quick Start Command**

To get started immediately:

```bash
# Clone the repository and run the integration test
git clone <repository>
cd nellia-prospector
chmod +x test_integration.sh
./test_integration.sh
```

## 📞 **Support & Troubleshooting**

### Common Issues
- **Port conflicts**: Check if ports 3000, 5001, 5173 are available
- **API key errors**: Verify all API keys are properly configured
- **Database connection**: Ensure PostgreSQL and Redis are running
- **MCP server errors**: Check database initialization and permissions

### Getting Help
- Check logs in each component directory
- Review environment variable configuration
- Test individual components before integration
- Use the provided test scripts for validation

---

**Next Action**: Start with Phase 1, Step 1 - MCP Server setup and basic functionality testing.
