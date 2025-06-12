# Real-Time Lead Enrichment Integration Plan

## 🎯 Goal
Create a seamless real-time flow where users can see leads being harvested, enriched through the agent pipeline, and updated in the CRM board with full visibility of the enrichment process.

## 🔄 Complete Flow Architecture

```
User Starts Prospecting → Harvest Leads → Real-time Pipeline → Webhook Events → WebSocket → CRM Updates
```

### Detailed Flow:
1. **User triggers prospecting** via webapp
2. **Harvest leads** with ADK1 → immediate CRM visibility  
3. **Pipeline processes each lead** → real-time status updates
4. **Agent enrichment** → progress updates per agent
5. **Final enriched lead** → complete data in CRM
6. **Pipeline completion** → quota updates

## 🛠️ Implementation Tasks

### 1. **MCP Server Webhook Integration** 
**File**: `prospect/mcp_server.py`

**Current Issue**: Events are streamed but not sent to webapp webhook
**Solution**: Add webhook posting capability to send events to webapp

```python
# Add to mcp_server.py
import httpx
import asyncio
from typing import Dict, Any

class WebhookEventSender:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.client = httpx.AsyncClient()
    
    async def send_event(self, event: Dict[str, Any]):
        """Send pipeline event to webapp webhook"""
        try:
            response = await self.client.post(
                f"{self.webhook_url}/queue/mcp/event-stream",
                json=event,
                timeout=30.0
            )
            if response.status_code != 200:
                logger.warning(f"Webhook failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Webhook error: {e}")

# Integrate webhook sending in the streaming response
```

### 2. **Event Routing Enhancement**
**File**: `prospect/pipeline_orchestrator.py`

**Enhancement**: Ensure all events include proper user context and are routed to webhook

```python
async def _enrich_lead(self, lead_data: Dict, lead_id: str) -> AsyncIterator[Dict]:
    # Current implementation + webhook routing
    async for event in self.hybrid_orchestrator._enrich_lead(lead_data, lead_id):
        # Add user context to every event
        event["user_id"] = self.user_id
        event["job_id"] = self.job_id
        
        # Send to webapp webhook
        if hasattr(self, 'webhook_sender'):
            await self.webhook_sender.send_event(event)
            
        yield event
```

### 3. **Lead State Management**
**File**: `webapp/backend/src/modules/mcp-webhook/mcp-webhook.service.ts`

**Enhancement**: Better lead lifecycle management with intermediate states

```typescript
enum LeadEnrichmentState {
  HARVESTED = 'harvested',
  ANALYZING = 'analyzing', 
  QUALIFYING = 'qualifying',
  STRATEGIZING = 'strategizing',
  FINALIZING = 'finalizing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

// Map agent events to enrichment states
private mapEventToState(eventType: string): LeadEnrichmentState {
  const stateMap = {
    'lead_analysis_start': LeadEnrichmentState.ANALYZING,
    'qualification_start': LeadEnrichmentState.QUALIFYING,
    'strategy_generation_start': LeadEnrichmentState.STRATEGIZING,
    'lead_enrichment_end': LeadEnrichmentState.COMPLETED
  };
  return stateMap[eventType] || LeadEnrichmentState.HARVESTED;
}
```

### 4. **Enhanced WebSocket Events**
**File**: `webapp/backend/src/modules/websocket/websocket.service.ts`

**Enhancement**: Add granular enrichment progress events

```typescript
emitLeadEnrichmentProgress(userId: string, data: {
  leadId: string;
  currentAgent: string;
  agentDescription: string;
  progressPercentage: number;
  estimatedTimeRemaining?: number;
  currentState: LeadEnrichmentState;
}) {
  this.sendToUserRoom(userId, 'lead-enrichment-progress', {
    type: WebSocketMessageType.LEAD_ENRICHMENT_PROGRESS,
    data,
    timestamp: new Date().toISOString(),
  });
}
```

### 5. **Frontend Real-Time Progress**
**File**: `webapp/frontend/src/components/CRMBoard.tsx`

**Enhancement**: Show detailed enrichment progress in real-time

```tsx
// Add enrichment progress visualization
const EnrichmentProgressCard = ({ lead, progressData }) => (
  <div className="border-l-4 border-blue-500 bg-slate-800 p-3 rounded">
    <div className="flex justify-between items-center mb-2">
      <span className="text-sm font-medium">{lead.company_name}</span>
      <Badge variant="outline" className="text-xs">
        {progressData?.currentAgent || 'Processing'}
      </Badge>
    </div>
    
    <div className="space-y-2">
      <div className="w-full bg-slate-700 rounded-full h-2">
        <div 
          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progressData?.progressPercentage || 0}%` }}
        />
      </div>
      
      <div className="text-xs text-slate-400">
        {progressData?.agentDescription || 'Initializing enrichment...'}
      </div>
      
      {progressData?.estimatedTimeRemaining && (
        <div className="text-xs text-slate-500">
          Est. {progressData.estimatedTimeRemaining}s remaining
        </div>
      )}
    </div>
  </div>
);
```

## 📋 Implementation Steps

### Phase 1: Core Integration (Priority 1)
1. ✅ **Webhook Event Sender**: Add webhook posting to MCP server
2. ✅ **Event User Context**: Ensure all events include user_id
3. ✅ **Basic State Updates**: Map core events to lead states  
4. ✅ **Frontend Reception**: Update CRM board to show enrichment progress

### Phase 2: Enhanced Visibility (Priority 2)  
1. ✅ **Agent Progress Tracking**: Individual agent status updates
2. ✅ **Time Estimation**: Progress percentage and ETA
3. ✅ **Error Handling**: Graceful failure states and retries
4. ✅ **Performance Metrics**: Track enrichment performance

### Phase 3: Production Polish (Priority 3)
1. ✅ **Connection Recovery**: Handle webhook/websocket failures  
2. ✅ **Rate Limiting**: Prevent event flooding
3. ✅ **Monitoring**: Health checks and alerting
4. ✅ **Analytics**: User engagement and system performance

## 🔧 Configuration Required

### Environment Variables
```bash
# prospect/.env
WEBAPP_WEBHOOK_URL=http://webapp-backend:3001
WEBAPP_WEBHOOK_ENABLED=true

# webapp/backend/.env  
MCP_SERVER_URL=http://prospect:5001
WEBHOOK_SECRET=your-webhook-secret
```

### URL Endpoints
```
MCP Server: http://prospect:5001/api/v2/execute_streaming_prospect
Webapp Webhook: http://webapp-backend:3001/mcp/webhook/event-stream
WebSocket: ws://webapp-backend:3001/socket.io
```

## 🎯 Expected User Experience

1. **Prospect Initiation**: User clicks "Start Prospecting" → immediate feedback
2. **Lead Discovery**: Leads appear in "Harvesting & Enriching" column in real-time
3. **Enrichment Progress**: Each lead shows current agent and progress bar
4. **Agent Visibility**: Users see which agent is working on each lead
5. **Completion**: Leads move to appropriate CRM stage with full enrichment data
6. **Error Handling**: Failed enrichments show clear error messages
7. **Quota Updates**: Real-time quota consumption feedback

## 🔍 Testing Strategy

### Integration Tests
```bash
# Test webhook integration
curl -X POST http://localhost:3001/mcp/webhook/event-stream \
  -H "Content-Type: application/json" \
  -d '{"event_type": "lead_generated", "user_id": "test", "lead_data": {...}}'

# Test WebSocket events  
wscat -c ws://localhost:3001/socket.io

# Test end-to-end flow
npm run test:e2e -- --grep "lead enrichment flow"
```

### Manual Testing Checklist
- [ ] Start prospecting job
- [ ] Verify leads appear immediately in CRM
- [ ] Confirm real-time progress updates  
- [ ] Check agent status visibility
- [ ] Validate completion/error states
- [ ] Verify quota updates
- [ ] Test connection recovery

## 🚀 Implementation Priority

**Critical Path** (Must Complete):
1. MCP Server webhook integration
2. Event user context propagation  
3. Frontend progress visualization
4. Error state handling

**Enhancement** (Nice to Have):
1. Detailed agent progress
2. Time estimation
3. Performance analytics
4. Advanced error recovery

## 📈 Success Metrics

1. **Real-time Visibility**: Users see lead updates within 2 seconds
2. **Progress Clarity**: Clear agent status and progress for each lead
3. **Error Transparency**: Failed enrichments show actionable errors
4. **Performance**: No dropped events or connection issues
5. **User Experience**: Smooth, responsive CRM board updates

This integration will provide users with complete visibility into the AI-powered lead generation and enrichment process, creating a professional, production-ready experience.
