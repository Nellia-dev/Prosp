# Nellia Prospector MCP Server Integration Guide

## 📋 Overview

This guide describes the integration between the Nellia Prospector Platform components and the Mission Control Panel (MCP) Server. The MCP server provides real-time monitoring and tracking of AI agent processing pipelines.

**⚠️ Note**: This guide has been updated to reflect the new MCP server implementation located at `prospect/mcp-server/`. The previous WebSocket-based approach has been replaced with a Flask REST API for better reliability and monitoring capabilities.

---

## 🏗️ Architecture Overview

The MCP Server acts as a central monitoring hub between:
- **Prospect Core**: Python AI processing engine
- **Backend API**: NestJS application 
- **Frontend Dashboard**: React interface for real-time monitoring

```
┌─────────────────────────────────────────────────────┐
│                  Integration Flow                    │
├─────────────────────────────────────────────────────┤
│  Frontend Dashboard (React)                         │
│  └── WebSocket ──┐                                  │
│                  │                                  │
│  Backend API (NestJS)                               │
│  ├── MCP Service ──┼─── HTTP REST ───┐              │
│  └── WebSocket ────┘                 │              │
│                                      │              │
│  MCP Server (Flask)                  │              │
│  ├── REST API ──────────────────────┘              │
│  ├── SQLite Database                                │
│  └── Real-time Status Tracking                     │
│                                      │              │
│  Prospect Core (Python AI)          │              │
│  └── Enhanced Lead Processor ───────┘              │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Current MCP Server Implementation

### Location and Structure
```
prospect/mcp-server/
├── app.py              # Flask REST API server
├── database.py         # SQLite database management
├── models.py           # SQLAlchemy ORM models
├── data_models.py      # Pydantic validation schemas
├── requirements.txt    # Python dependencies
└── init_db.py         # Database initialization script
```

### Key Features
- **REST API**: HTTP endpoints for lead tracking and metrics
- **Real-time Monitoring**: Live status updates for lead processing
- **Agent Execution Tracking**: Detailed logging of each AI agent's performance
- **Performance Metrics**: Success rates, processing times, system health
- **SQLite Database**: Persistent storage for processing history

---

## 🚀 Integration Points

### 1. Prospect Core → MCP Server

The Enhanced Lead Processor reports events to the MCP server:

```python
# prospect/agents/enhanced_lead_processor.py
import requests
from config import get_config

class EnhancedLeadProcessor:
    def __init__(self):
        self.config = get_config()
        self.mcp_enabled = self.config.get("ENABLE_MCP_REPORTING", False)
        self.mcp_url = self.config.get("MCP_SERVER_URL", "http://localhost:5001")
    
    async def process_lead(self, lead, run_id):
        lead_id = self.generate_lead_id(lead)
        
        # Start lead processing tracking
        if self.mcp_enabled:
            await self.report_lead_start(lead_id, run_id)
        
        # Process through agents
        for agent in self.agents:
            start_time = datetime.utcnow()
            try:
                result = await agent.process(lead)
                # Report success
                if self.mcp_enabled:
                    await self.report_agent_event(lead_id, agent.name, "SUCCESS", 
                                                 start_time, result)
            except Exception as e:
                # Report failure
                if self.mcp_enabled:
                    await self.report_agent_event(lead_id, agent.name, "FAILED", 
                                                 start_time, error=str(e))
    
    async def report_lead_start(self, lead_id, run_id):
        payload = {
            "lead_id": lead_id,
            "run_id": run_id,
            "url": lead.url if hasattr(lead, 'url') else None,
            "start_time": datetime.utcnow().isoformat()
        }
        response = requests.post(f"{self.mcp_url}/api/lead/start", json=payload)
        
    async def report_agent_event(self, lead_id, agent_name, status, start_time, 
                                result=None, error=None):
        payload = {
            "agent_name": agent_name,
            "status": status,
            "start_time": start_time.isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "processing_time_seconds": (datetime.utcnow() - start_time).total_seconds(),
            "output_json": json.dumps(result.model_dump()) if result else None,
            "error_message": error
        }
        response = requests.post(f"{self.mcp_url}/api/lead/{lead_id}/event", json=payload)
```

### 2. Backend API → MCP Server

The NestJS backend integrates with the MCP server for monitoring:

```typescript
// webapp/backend/src/modules/mcp/mcp.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class McpService {
  private readonly logger = new Logger(McpService.name);
  private readonly mcpBaseUrl: string;

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
  ) {
    this.mcpBaseUrl = this.configService.get('MCP_SERVER_URL') || 'http://localhost:5001';
  }

  async getLeadStatus(leadId: string) {
    try {
      const response = await this.httpService
        .get(`${this.mcpBaseUrl}/api/lead/${leadId}/status`)
        .toPromise();
      return response.data;
    } catch (error) {
      this.logger.error(`Failed to get lead status for ${leadId}:`, error.message);
      throw error;
    }
  }

  async getRunStatus(runId: string) {
    try {
      const response = await this.httpService
        .get(`${this.mcpBaseUrl}/api/run/${runId}/status`)
        .toPromise();
      return response.data;
    } catch (error) {
      this.logger.error(`Failed to get run status for ${runId}:`, error.message);
      throw error;
    }
  }

  async getSystemMetrics() {
    try {
      const response = await this.httpService
        .get(`${this.mcpBaseUrl}/metrics`)
        .toPromise();
      return response.data;
    } catch (error) {
      this.logger.error('Failed to get MCP system metrics:', error.message);
      throw error;
    }
  }

  async healthCheck() {
    try {
      const response = await this.httpService
        .get(`${this.mcpBaseUrl}/health`)
        .toPromise();
      return response.data;
    } catch (error) {
      this.logger.warn('MCP server health check failed:', error.message);
      return { status: 'unhealthy', error: error.message };
    }
  }
}
```

### 3. Frontend → Backend → MCP Server

The React frontend receives real-time updates via WebSocket:

```typescript
// webapp/frontend/src/hooks/useLeadProcessingStatus.ts
import { useState, useEffect } from 'react';
import { useWebSocket } from '@/contexts/WebSocketContext';
import { api } from '@/services/api';

interface LeadProcessingStatus {
  leadId: string;
  status: 'PENDING' | 'ACTIVE' | 'COMPLETED' | 'FAILED';
  currentAgent?: string;
  agentExecutions: AgentExecution[];
  progress: number;
}

export const useLeadProcessingStatus = (leadId: string) => {
  const [status, setStatus] = useState<LeadProcessingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const { socket } = useWebSocket();

  useEffect(() => {
    // Initial status fetch
    const fetchStatus = async () => {
      try {
        const response = await api.get(`/leads/${leadId}/processing-status`);
        setStatus(response.data);
      } catch (error) {
        console.error('Failed to fetch lead status:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();

    // Listen for real-time updates
    if (socket) {
      socket.on(`lead:${leadId}:status`, (updatedStatus) => {
        setStatus(updatedStatus);
      });

      socket.on(`lead:${leadId}:agent-complete`, (agentEvent) => {
        setStatus(prev => prev ? {
          ...prev,
          agentExecutions: [...prev.agentExecutions, agentEvent],
          currentAgent: agentEvent.agent_name,
          progress: calculateProgress(agentEvent.agent_name)
        } : null);
      });
    }

    return () => {
      if (socket) {
        socket.off(`lead:${leadId}:status`);
        socket.off(`lead:${leadId}:agent-complete`);
      }
    };
  }, [leadId, socket]);

  return { status, loading };
};
```

---

## 📊 MCP Server API Endpoints

### Lead Processing Endpoints

```bash
# Start lead processing tracking
POST /api/lead/start
Content-Type: application/json
{
  "lead_id": "unique_lead_identifier",
  "run_id": "processing_run_identifier", 
  "url": "https://company.com",
  "start_time": "2025-01-01T10:00:00Z"
}

# Record agent execution event
POST /api/lead/{lead_id}/event
Content-Type: application/json
{
  "agent_name": "TavilyEnrichmentAgent",
  "status": "SUCCESS",
  "start_time": "2025-01-01T10:00:00Z",
  "end_time": "2025-01-01T10:00:15Z", 
  "processing_time_seconds": 15.2,
  "output_json": "{\"analysis\": \"...\"}",
  "metrics_json": "{\"llm_calls\": 3}"
}

# Get lead processing status
GET /api/lead/{lead_id}/status
Response:
{
  "lead_status": {
    "lead_id": "...",
    "status": "ACTIVE",
    "current_agent": "PersonaCreationAgent",
    "start_time": "...",
    "last_update_time": "..."
  },
  "agent_executions": [
    {
      "agent_name": "LeadIntakeAgent",
      "status": "SUCCESS",
      "processing_time_seconds": 5.2,
      "output_json": "..."
    }
  ]
}

# Get run processing status  
GET /api/run/{run_id}/status
Response:
{
  "run_id": "run_123",
  "leads": [
    {
      "lead_id": "lead_1",
      "status": "COMPLETED",
      "start_time": "...",
      "end_time": "..."
    }
  ]
}
```

### System Monitoring Endpoints

```bash
# Health check
GET /health
Response:
{
  "status": "healthy",
  "timestamp": "2025-01-01T10:00:00Z",
  "database": "connected",
  "version": "1.0.0"
}

# System metrics
GET /metrics  
Response:
{
  "total_leads": 1250,
  "active_leads": 15,
  "completed_leads": 1180,
  "failed_leads": 55,
  "success_rate": 94.4,
  "recent_leads_24h": 45
}
```

---

## 🔧 Configuration

### Environment Variables

#### Prospect Core Configuration
```env
# prospect/.env
ENABLE_MCP_REPORTING=true
MCP_SERVER_URL=http://localhost:5001
MCP_TIMEOUT=30
```

#### Backend Configuration  
```env
# webapp/backend/.env
MCP_SERVER_URL=http://localhost:5001
MCP_SERVER_TIMEOUT=30000
MCP_HEALTH_CHECK_INTERVAL=60000
```

#### MCP Server Configuration
```env
# prospect/mcp-server/.env (optional)
FLASK_ENV=development
FLASK_DEBUG=true
DATABASE_URL=sqlite:///./mcp_server_data.db
```

---

## 🚀 Deployment & Operations

### Starting the MCP Server

```bash
# Development mode
cd prospect/mcp-server
python app.py

# Production mode with Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app

# Docker deployment
docker build -t nellia-mcp-server .
docker run -p 5001:5001 nellia-mcp-server
```

### Database Management

```bash
# Initialize database
cd prospect/mcp-server
python -c "from database import init_db; init_db()"

# Or use the init script
python init_db.py

# Backup database
cp mcp_server_data.db mcp_server_data.db.backup
```

### Monitoring & Logging

```bash
# Check MCP server health
curl http://localhost:5001/health

# Get processing metrics
curl http://localhost:5001/metrics

# Monitor logs (if using systemd)
journalctl -u nellia-mcp-server -f
```

---

## 🔍 Troubleshooting

### Common Issues

**MCP Server Connection Failed**
```bash
# Check if server is running
curl http://localhost:5001/health

# Check backend logs
cd webapp/backend && npm run start:dev

# Verify environment variables
echo $MCP_SERVER_URL
```

**Database Initialization Errors**
```bash
# Reinitialize database
cd prospect/mcp-server
rm -f mcp_server_data.db
python init_db.py
```

**Missing Agent Events**
```bash
# Verify MCP reporting is enabled
grep ENABLE_MCP_REPORTING prospect/.env

# Check prospect core logs
cd prospect && python enhanced_main.py --log-level DEBUG
```

**Frontend Not Receiving Updates**
```bash
# Check WebSocket connection
# Open browser dev tools -> Network -> WS

# Verify backend WebSocket gateway
cd webapp/backend && npm run start:dev
```

---

## 📈 Performance Considerations

### Optimization Tips

1. **Database Performance**
   - Regular database cleanup for old records
   - Index optimization for frequently queried fields
   - Consider PostgreSQL for high-volume deployments

2. **API Response Times**
   - Implement caching for frequently accessed data
   - Use connection pooling for database connections
   - Add request rate limiting

3. **Real-time Updates**
   - Batch WebSocket messages to reduce network overhead
   - Implement client-side caching of agent status
   - Use server-sent events (SSE) as WebSocket alternative

4. **Monitoring & Alerting**
   - Set up health check monitoring
   - Configure alerts for processing failures
   - Track processing time trends and anomalies

---

## 🔮 Future Enhancements

### Planned Improvements

1. **Advanced Analytics**
   - Processing time trends and optimization suggestions
   - Agent performance comparisons and recommendations
   - Lead quality scoring improvements based on outcomes

2. **Scalability Features**
   - Horizontal scaling with load balancing
   - Message queue integration (Redis/RabbitMQ)
   - Distributed processing support

3. **Enhanced Monitoring**
   - Real-time performance dashboards
   - Predictive analysis for processing bottlenecks
   - Automated scaling based on load

4. **Integration Improvements**
   - GraphQL subscription support
   - gRPC for high-performance communication
   - Event sourcing for complete audit trails

---

## 📞 Support

For issues related to MCP server integration:

1. **Check the logs**: MCP server logs provide detailed error information
2. **Verify configuration**: Ensure all environment variables are properly set
3. **Test connectivity**: Use curl or Postman to test MCP endpoints directly
4. **Review documentation**: This guide covers most common integration scenarios

**Contact**: contato@nellia.com.br for technical support.

---

*Last Updated: January 4, 2025*
*MCP Server Version: 1.0.0*
