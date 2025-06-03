# Google Agent2Agent (A2A) Protocol Integration Guide

## Overview

Google's Agent2Agent (A2A) Protocol is an open standard designed to enable communication and interoperability between AI agents built on different frameworks. This document outlines how A2A could be integrated into the Nellia Prospector system to create a distributed, scalable architecture.

**Official Repository**: [https://github.com/google-a2a/A2A](https://github.com/google-a2a/A2A)

## What is A2A?

A2A is not a message bus or queue system, but rather a protocol specification that enables:

- **Standardized Communication**: JSON-RPC 2.0 over HTTP(S) for agent-to-agent communication
- **Agent Discovery**: Agents publish "Agent Cards" describing their capabilities
- **Flexible Interaction Patterns**: 
  - Synchronous request/response
  - Streaming (Server-Sent Events)
  - Asynchronous push notifications
- **Rich Data Exchange**: Support for text, files, and structured JSON data
- **Agent Opacity**: Agents can collaborate without exposing internal state, memory, or tools

## Benefits for Nellia Prospector

Implementing A2A would transform our monolithic pipeline into a distributed system with these advantages:

1. **Scalability**: Each agent can be scaled independently based on load
2. **Language Agnostic**: Agents could be implemented in different programming languages
3. **Fault Tolerance**: Individual agent failures won't crash the entire pipeline
4. **Interoperability**: Could integrate with other A2A-compliant agents from different vendors
5. **Flexibility**: Easy to add, remove, or replace agents without changing the core system

## Proposed Architecture

### Current Architecture (Monolithic)
```
Harvester Output → Lead Intake → Analysis → Persona → Strategy → Message → Output
```

### A2A-Enabled Architecture (Distributed)
```
┌─────────────┐     A2A      ┌──────────────┐     A2A      ┌──────────────┐
│Lead Intake  │────────────▶│Lead Analysis │────────────▶│Persona Agent │
│Agent Server │◀────────────│Agent Server  │◀────────────│   Server     │
└─────────────┘              └──────────────┘              └──────────────┘
       │                            │                             │
   Agent Card                  Agent Card                    Agent Card
       
       ▼                            ▼                             ▼
┌─────────────┐     A2A      ┌──────────────┐     A2A      ┌──────────────┐
│  Strategy   │────────────▶│   Message    │────────────▶│   Output     │
│Agent Server │◀────────────│Agent Server  │◀────────────│  Formatter   │
└─────────────┘              └──────────────┘              └──────────────┘
```

## Implementation Steps

### 1. Install A2A SDK
```bash
pip install a2a-sdk
```

### 2. Create Agent Cards

Each agent needs an Agent Card describing its capabilities:

```python
# Example Agent Card for Lead Analysis Agent
{
    "id": "nellia-lead-analysis-agent",
    "name": "Nellia Lead Analysis Agent",
    "description": "Analyzes lead data to identify opportunities and relevance",
    "version": "1.0.0",
    "capabilities": {
        "input": {
            "accepts": ["ValidatedLead"],
            "format": "json"
        },
        "output": {
            "produces": ["AnalyzedLead"],
            "format": "json"
        }
    },
    "endpoint": "https://analysis.nellia.com/a2a",
    "authentication": {
        "type": "bearer",
        "required": true
    }
}
```

### 3. Implement A2A Server for Each Agent

```python
from a2a_sdk import A2AServer, A2ARequest, A2AResponse
from agents.lead_analysis_agent import LeadAnalysisAgent

class LeadAnalysisA2AServer:
    def __init__(self):
        self.server = A2AServer()
        self.agent = LeadAnalysisAgent()
        
    def register_handlers(self):
        @self.server.method("analyze_lead")
        async def analyze_lead(request: A2ARequest) -> A2AResponse:
            # Extract lead data from request
            lead_data = request.params.get("lead_data")
            
            # Process with our existing agent
            result = await self.agent.process(lead_data)
            
            # Return A2A response
            return A2AResponse(result=result)
```

### 4. Service Discovery

Agents discover each other through:
- Static configuration (URLs in config files)
- Service registry (e.g., Consul, etcd)
- DNS-based discovery

### 5. Orchestration

The main orchestrator would:
1. Discover available agents
2. Send harvester output to Lead Intake Agent via A2A
3. Chain agent calls based on responses
4. Handle errors and retries
5. Aggregate final results

## Migration Strategy

1. **Phase 1**: Keep current architecture, add A2A endpoints to existing agents
2. **Phase 2**: Test A2A communication between agents in staging
3. **Phase 3**: Gradually migrate to distributed deployment
4. **Phase 4**: Full A2A implementation with independent agent scaling

## Example A2A Message Flow

```json
// Request from Orchestrator to Lead Analysis Agent
{
    "jsonrpc": "2.0",
    "method": "analyze_lead",
    "params": {
        "lead_data": {
            "url": "https://example.com",
            "extracted_text": "Company description...",
            "product_context": "AI consulting services"
        }
    },
    "id": "123"
}

// Response from Lead Analysis Agent
{
    "jsonrpc": "2.0",
    "result": {
        "analysis": {
            "company_sector": "Technology",
            "relevance_score": 0.85,
            "opportunities": ["Digital transformation", "AI adoption"]
        }
    },
    "id": "123"
}
```

## Security Considerations

- **Authentication**: Use OAuth2 or API keys for agent authentication
- **Encryption**: All A2A communication should use HTTPS
- **Rate Limiting**: Implement rate limits to prevent abuse
- **Audit Logging**: Log all inter-agent communications

## Monitoring and Observability

With A2A implementation, add:
- Distributed tracing (OpenTelemetry)
- Centralized logging (ELK stack)
- Metrics collection (Prometheus)
- Health checks for each agent

## Future Possibilities

With A2A, Nellia Prospector could:
- Integrate with third-party A2A agents for enhanced capabilities
- Offer individual agents as services to other companies
- Create a marketplace of specialized processing agents
- Enable customers to bring their own agents

## Resources

- [A2A Protocol Specification](https://google-a2a.github.io/A2A/)
- [A2A Python SDK Documentation](https://pypi.org/project/a2a-sdk/)
- [A2A GitHub Repository](https://github.com/google-a2a/A2A)
- [A2A Examples and Samples](https://github.com/google-a2a/A2A/tree/main/samples) 