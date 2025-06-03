# Nellia Prospector - MCP Server Integration Guide

## 📋 Overview

This guide describes the integration between the Nellia Prospector webapp and the new MCP (Mission Control Panel) Server. The MCP Server has been redesigned as a Flask-based tracking system that monitors the real-time progress and results of leads processed by the Enhanced Nellia Prospector pipeline.

**⚠️ Important Update**: This document replaces the previous Python MCP server guide. The new MCP server is now located at `prospect/mcp-server/` and provides a different architecture focused on tracking and monitoring rather than direct agent execution.

---

## 🏗️ New Architecture Overview

The updated system consists of:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Updated Integration Architecture              │
├─────────────────────────────────────────────────────────────────┤
│  React Frontend (webapp/frontend)                              │
│  ├── Real-time dashboards                                      │
│  ├── Lead status monitoring                                    │
│  ├── Agent progress tracking                                   │
│  └── Business context management                               │
├─────────────────────────────────────────────────────────────────┤
│  NestJS Backend (webapp/backend)                               │
│  ├── REST API endpoints                                        │
│  ├── WebSocket communication                                   │
│  ├── MCP server integration                                    │
│  └── Database management                                       │
├─────────────────────────────────────────────────────────────────┤
│  MCP Server (prospect/mcp-server) - NEW ARCHITECTURE           │
│  ├── Flask-based tracking server                               │
│  ├── Real-time progress monitoring                             │
│  ├── Agent execution recording                                 │
│  ├── Lead status management                                    │
│  └── SQLite database for tracking                              │
├─────────────────────────────────────────────────────────────────┤
│  Enhanced Lead Processor (prospect)                            │
│  ├── Multi-agent AI pipeline                                   │
│  ├── Direct MCP reporting integration                          │
│  ├── 15-step processing workflow                               │
│  └── Business intelligence generation                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 What Changed

### Previous Architecture (Deprecated)
- Direct WebSocket MCP server for agent execution
- Python agents managed via WebSocket messages
- Real-time agent communication through WebSocket

### New Architecture (Current)
- **MCP Server**: Flask-based tracking and monitoring system
- **AI Processing**: Standalone Enhanced Lead Processor with direct MCP reporting
- **Integration**: HTTP API communication between components
- **Monitoring**: Real-time progress tracking and status updates

---

## 🚀 Quick Setup Guide

### 1. MCP Server Setup

The MCP server is now located at `prospect/mcp-server/` and provides tracking capabilities:

```bash
# Navigate to MCP server directory
cd prospect/mcp-server

# Initialize the database
python -c "from database import init_db; init_db()"

# Start the MCP server
python app.py
```

The MCP server will run on `http://localhost:5001` and provide:
- Lead processing state tracking
- Agent execution monitoring
- Progress reporting APIs
- Real-time status updates

### 2. Backend Integration

The NestJS backend integrates with the MCP server via HTTP API:

```typescript
// Example: Check MCP server health
const mcpHealth = await fetch('http://localhost:5001/api/health');

// Example: Get lead status
const leadStatus = await fetch(`http://localhost:5001/api/lead/${leadId}/status`);

// Example: Get run status for multiple leads
const runStatus = await fetch(`http://localhost:5001/api/run/${runId}/status`);
```

### 3. Enhanced Processor Integration

The Enhanced Lead Processor automatically reports to the MCP server:

```bash
# Enable MCP reporting in prospect/.env
ENABLE_MCP_REPORTING=true
MCP_SERVER_URL=http://127.0.0.1:5001

# Process leads with automatic MCP tracking
cd prospect
python enhanced_main.py leads.json -p "Your product/service"
```

---

## 📊 MCP Server API Reference

### Core Endpoints

#### Start Lead Processing
```http
POST /api/lead/start
Content-Type: application/json

{
  "lead_id": "unique_lead_identifier",
  "run_id": "unique_run_identifier", 
  "url": "http://example.com",
  "start_time": "2024-01-01T10:00:00.000Z",
  "current_agent": "LeadIntakeAgent"
}
```

#### Record Agent Event
```http
POST /api/lead/{lead_id}/event
Content-Type: application/json

{
  "agent_name": "TavilyEnrichmentAgent",
  "status": "SUCCESS",
  "start_time": "2024-01-01T10:00:00.000Z",
  "end_time": "2024-01-01T10:00:30.000Z",
  "processing_time_seconds": 30.5,
  "output_json": "{\"enriched_data\": \"...\"}",
  "metrics_json": "{\"llm_calls\": 2, \"tokens_used\": 1500}",
  "error_message": null
}
```

#### Get Lead Status
```http
GET /api/lead/{lead_id}/status

Response:
{
  "lead_status": {
    "lead_id": "lead-123",
    "status": "ACTIVE",
    "current_agent": "PersonaCreationAgent",
    "start_time": "2024-01-01T10:00:00.000Z",
    "last_update_time": "2024-01-01T10:05:00.000Z"
  },
  "agent_executions": [
    {
      "agent_name": "LeadIntakeAgent",
      "status": "SUCCESS",
      "processing_time_seconds": 15.2,
      "output_json": "{...}",
      "end_time": "2024-01-01T10:02:00.000Z"
    }
  ]
}
```

#### Get Run Status
```http
GET /api/run/{run_id}/status

Response:
{
  "run_id": "run-456",
  "leads": [
    {
      "lead_id": "lead-123",
      "status": "COMPLETED",
      "final_package_summary": "{\"roi_potential\": 0.87}"
    },
    {
      "lead_id": "lead-124", 
      "status": "ACTIVE",
      "current_agent": "StrategyGenerationAgent"
    }
  ]
}
```

---

## 🔧 Backend Integration Implementation

### MCP Service Integration

Update your NestJS backend's MCP service to integrate with the new tracking server:

```typescript
// src/modules/mcp/mcp.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class McpService {
  private readonly logger = new Logger(McpService.name);
  private readonly mcpServerUrl: string;

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
  ) {
    this.mcpServerUrl = this.configService.get<string>('MCP_SERVER_URL', 'http://localhost:5001');
  }

  async startLeadProcessing(leadData: {
    lead_id: string;
    run_id: string;
    url?: string;
    current_agent?: string;
  }) {
    try {
      const response = await this.httpService.post(
        `${this.mcpServerUrl}/api/lead/start`,
        {
          ...leadData,
          start_time: new Date().toISOString(),
        }
      ).toPromise();
      
      return response.data;
    } catch (error) {
      this.logger.error('Failed to start lead processing in MCP', error);
      throw error;
    }
  }

  async getLeadStatus(leadId: string) {
    try {
      const response = await this.httpService.get(
        `${this.mcpServerUrl}/api/lead/${leadId}/status`
      ).toPromise();
      
      return response.data;
    } catch (error) {
      this.logger.error(`Failed to get lead status for ${leadId}`, error);
      throw error;
    }
  }

  async getRunStatus(runId: string) {
    try {
      const response = await this.httpService.get(
        `${this.mcpServerUrl}/api/run/${runId}/status`
      ).toPromise();
      
      return response.data;
    } catch (error) {
      this.logger.error(`Failed to get run status for ${runId}`, error);
      throw error;
    }
  }

  async checkMcpHealth() {
    try {
      const response = await this.httpService.get(
        `${this.mcpServerUrl}/api/health`
      ).toPromise();
      
      return { healthy: true, data: response.data };
    } catch (error) {
      this.logger.warn('MCP server health check failed', error);
      return { healthy: false, error: error.message };
    }
  }
}
```

### Lead Processing Controller Updates

```typescript
// src/modules/leads/leads.controller.ts
@Controller('api/leads')
export class LeadsController {
  constructor(
    private readonly leadsService: LeadsService,
    private readonly mcpService: McpService,
  ) {}

  @Post()
  async createLead(@Body() createLeadDto: CreateLeadDto) {
    // Create lead in main database
    const lead = await this.leadsService.create(createLeadDto);
    
    // Start tracking in MCP server
    const runId = uuidv4();
    await this.mcpService.startLeadProcessing({
      lead_id: lead.id,
      run_id: runId,
      url: lead.website,
      current_agent: 'LeadIntakeAgent'
    });

    // Trigger AI processing (via queue or direct call)
    await this.triggerLeadProcessing(lead, runId);

    return lead;
  }

  @Get(':id/status')
  async getLeadStatus(@Param('id') id: string) {
    // Get status from both main DB and MCP server
    const [leadData, mcpStatus] = await Promise.all([
      this.leadsService.findOne(id),
      this.mcpService.getLeadStatus(id)
    ]);

    return {
      lead: leadData,
      processing_status: mcpStatus
    };
  }

  @Get('run/:runId/status')
  async getRunStatus(@Param('runId') runId: string) {
    return this.mcpService.getRunStatus(runId);
  }

  private async triggerLeadProcessing(lead: Lead, runId: string) {
    // Implementation depends on your processing approach:
    // Option 1: Queue-based processing
    // await this.queueService.addLeadProcessingJob(lead, runId);
    
    // Option 2: Direct API call to processing service
    // await this.processingService.processLead(lead, runId);
    
    // Option 3: File-based processing
    // await this.createProcessingFile(lead, runId);
  }
}
```

---

## 🎯 Frontend Integration

### Real-time Status Updates

Update your React components to display real-time processing status:

```typescript
// components/LeadStatusCard.tsx
import { useState, useEffect } from 'react';

interface LeadStatusCardProps {
  leadId: string;
}

export function LeadStatusCard({ leadId }: LeadStatusCardProps) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`/api/leads/${leadId}/status`);
        const data = await response.json();
        setStatus(data.processing_status);
      } catch (error) {
        console.error('Failed to fetch lead status:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [leadId]);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="lead-status-card">
      <h3>Lead Processing Status</h3>
      <div className="status-info">
        <p><strong>Status:</strong> {status?.lead_status?.status}</p>
        <p><strong>Current Agent:</strong> {status?.lead_status?.current_agent}</p>
        <p><strong>Last Update:</strong> {new Date(status?.lead_status?.last_update_time).toLocaleString()}</p>
      </div>
      
      <div className="agent-history">
        <h4>Agent Execution History</h4>
        {status?.agent_executions?.map((execution, index) => (
          <div key={index} className="agent-execution">
            <span className="agent-name">{execution.agent_name}</span>
            <span className={`status ${execution.status.toLowerCase()}`}>
              {execution.status}
            </span>
            <span className="duration">
              {execution.processing_time_seconds}s
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Run Status Dashboard

```typescript
// components/RunStatusDashboard.tsx
export function RunStatusDashboard({ runId }: { runId: string }) {
  const [runStatus, setRunStatus] = useState(null);

  useEffect(() => {
    const fetchRunStatus = async () => {
      const response = await fetch(`/api/leads/run/${runId}/status`);
      const data = await response.json();
      setRunStatus(data);
    };

    fetchRunStatus();
    const interval = setInterval(fetchRunStatus, 10000);
    return () => clearInterval(interval);
  }, [runId]);

  return (
    <div className="run-status-dashboard">
      <h2>Processing Run: {runId}</h2>
      <div className="leads-grid">
        {runStatus?.leads?.map(lead => (
          <div key={lead.lead_id} className={`lead-card ${lead.status.toLowerCase()}`}>
            <h3>{lead.lead_id}</h3>
            <p>Status: {lead.status}</p>
            {lead.current_agent && <p>Current Agent: {lead.current_agent}</p>}
            {lead.final_package_summary && (
              <details>
                <summary>Final Results</summary>
                <pre>{JSON.stringify(JSON.parse(lead.final_package_summary), null, 2)}</pre>
              </details>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 🔧 Configuration

### Environment Variables

Update your environment configurations:

**webapp/backend/.env**:
```env
# MCP Server Configuration
MCP_SERVER_URL=http://localhost:5001
MCP_SERVER_TIMEOUT=30000
MCP_HEALTH_CHECK_INTERVAL=60000

# Processing Configuration
ENABLE_MCP_INTEGRATION=true
DEFAULT_RUN_TIMEOUT=300000
```

**prospect/.env**:
```env
# MCP Reporting Configuration
ENABLE_MCP_REPORTING=true
MCP_SERVER_URL=http://127.0.0.1:5001

# Processing Configuration
ENABLE_ENHANCED_PROCESSING=true
MAX_LEADS_PER_BATCH=100
```

---

## 🧪 Testing the Integration

### 1. Test MCP Server Health

```bash
# Check if MCP server is running
curl http://localhost:5001/api/health

# Expected response:
# {"status": "healthy", "timestamp": "2024-01-01T10:00:00.000Z"}
```

### 2. Test Lead Processing Flow

```bash
# 1. Start MCP server
cd prospect/mcp-server
python app.py

# 2. Start backend (in another terminal)
cd webapp/backend
npm run start:dev

# 3. Process a test lead (in another terminal)
cd prospect
echo '[{"url": "https://example.com", "company_name": "Test Company"}]' > test_lead.json
python enhanced_main.py test_lead.json -p "Test product"

# 4. Check status via API
curl http://localhost:5001/api/run/[run_id]/status
```

### 3. Test Frontend Integration

```bash
# Start frontend
cd webapp/frontend
npm run dev

# Navigate to http://localhost:5173
# Upload leads and monitor processing in real-time
```

---

## 🚨 Troubleshooting

### Common Issues

**MCP Server Connection Failed**
```bash
# Check if MCP server is running
ps aux | grep "python app.py"

# Check port availability
lsof -i :5001

# Restart MCP server
cd prospect/mcp-server
python app.py
```

**Database Initialization Issues**
```bash
# Reinitialize MCP database
cd prospect/mcp-server
python -c "import os; os.remove('mcp_server_data.db') if os.path.exists('mcp_server_data.db') else None"
python -c "from database import init_db; init_db()"
```

**Backend MCP Integration Issues**
```bash
# Check backend MCP service logs
cd webapp/backend
npm run start:dev
# Look for MCP-related error messages

# Test direct MCP communication
curl -X POST http://localhost:5001/api/lead/start \
  -H "Content-Type: application/json" \
  -d '{"lead_id": "test-123", "run_id": "test-run", "url": "https://example.com"}'
```

---

## 📈 Performance Monitoring

### Key Metrics to Track

1. **Lead Processing Times**
   - Time from start to completion
   - Individual agent execution times
   - Queue wait times

2. **System Health**
   - MCP server uptime
   - Database connection status
   - API response times

3. **Processing Success Rates**
   - Successful vs failed lead processing
   - Agent-specific success rates
   - Error patterns and frequencies

### Monitoring Dashboard

The frontend should display:
- Real-time processing statistics
- Agent performance metrics
- System health indicators
- Historical processing data

---

## 🔮 Future Enhancements

### Planned Improvements

1. **WebSocket Integration**: Real-time updates without polling
2. **Enhanced Error Handling**: Automatic retry and recovery mechanisms
3. **Performance Analytics**: Detailed processing metrics and optimization
4. **Scalability**: Support for multiple concurrent processing runs
5. **Integration APIs**: Direct CRM and external system integrations

### Migration Path

For teams currently using the old MCP server architecture:

1. **Phase 1**: Deploy new MCP server alongside existing system
2. **Phase 2**: Update backend to use new MCP APIs
3. **Phase 3**: Migrate frontend to new status monitoring
4. **Phase 4**: Deprecate old WebSocket-based system
5. **Phase 5**: Full cutover to new architecture

---

## 📞 Support

For integration support:

- **Technical Issues**: Check the troubleshooting section above
- **Architecture Questions**: Review the component documentation
- **Performance Issues**: Monitor the metrics dashboard
- **Feature Requests**: Submit via GitHub issues

---

**Built for seamless integration between modern web technologies and advanced AI processing.**

*This guide ensures smooth operation of the complete Nellia Prospector platform with real-time monitoring and tracking capabilities.*
