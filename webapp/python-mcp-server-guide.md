# Python MCP Server Implementation Guide

## 📋 Overview

This guide provides step-by-step instructions to create a Python MCP (Model Context Protocol) server that interfaces with the Nellia Prospector NestJS backend. The MCP server will handle AI agent operations, lead processing, and business intelligence tasks.

---

## 🏗️ Project Structure

```
nellia-mcp-server/
├── requirements.txt
├── .env
├── main.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── core/
│   ├── __init__.py
│   ├── websocket_server.py
│   └── message_handler.py
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── lead_processor.py
│   ├── researcher.py
│   ├── persona_analyzer.py
│   ├── strategy_generator.py
│   └── message_creator.py
├── services/
│   ├── __init__.py
│   ├── lead_service.py
│   ├── business_context_service.py
│   └── metrics_service.py
└── utils/
    ├── __init__.py
    ├── logger.py
    └── helpers.py
```

---

## 🚀 Step 1: Project Setup

### 1.1 Create Project Directory

```bash
mkdir nellia-mcp-server
cd nellia-mcp-server
```

### 1.2 Create Python Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 1.3 Create requirements.txt

```txt
# WebSocket and networking
websockets==12.0
asyncio-mqtt==0.13.0

# AI and NLP
openai==1.6.1
anthropic==0.7.8
langchain==0.1.0
langchain-openai==0.0.2

# Data processing
pandas==2.1.4
numpy==1.24.3
pydantic==2.5.2

# Web scraping and research
aiohttp==3.9.1
beautifulsoup4==4.12.2
selenium==4.16.2

# Environment and configuration
python-dotenv==1.0.0
pyyaml==6.0.1

# Logging and monitoring
structlog==23.2.0

# Database (optional for local caching)
sqlalchemy==2.0.23
aiosqlite==0.19.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```

### 1.4 Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 Step 2: Configuration

### 2.1 Create .env File

```env
# MCP Server Configuration
MCP_HOST=localhost
MCP_PORT=8000
MCP_DEBUG=true

# Backend Connection
BACKEND_HOST=localhost
BACKEND_PORT=3000

# AI Provider Configuration
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Research Tools
SERP_API_KEY=your_serp_api_key_here
APOLLO_API_KEY=your_apollo_api_key_here

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Rate Limiting
MAX_CONCURRENT_TASKS=10
REQUEST_TIMEOUT=30
```

### 2.2 Create config/settings.py

```python
import os
from typing import Optional
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # MCP Server
    mcp_host: str = Field(default="localhost", env="MCP_HOST")
    mcp_port: int = Field(default=8000, env="MCP_PORT")
    mcp_debug: bool = Field(default=False, env="MCP_DEBUG")
    
    # Backend Connection
    backend_host: str = Field(default="localhost", env="BACKEND_HOST")
    backend_port: int = Field(default=3000, env="BACKEND_PORT")
    
    # AI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Research APIs
    serp_api_key: Optional[str] = Field(default=None, env="SERP_API_KEY")
    apollo_api_key: Optional[str] = Field(default=None, env="APOLLO_API_KEY")
    
    # Performance
    max_concurrent_tasks: int = Field(default=10, env="MAX_CONCURRENT_TASKS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## 🎯 Step 3: Core WebSocket Server

### 3.1 Create core/websocket_server.py

```python
import asyncio
import json
import websockets
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from config.settings import settings
from core.message_handler import MessageHandler
from utils.logger import get_logger

logger = get_logger(__name__)

class MCPServer:
    def __init__(self):
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.message_handler = MessageHandler()
        self.running = False
        
    async def register_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Register a new client connection."""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
        try:
            await self.handle_client(websocket, client_id)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, client_id: str):
        """Handle messages from a client."""
        async for message in websocket:
            try:
                data = json.loads(message)
                response = await self.message_handler.handle_message(data)
                await websocket.send(json.dumps(response))
                
            except json.JSONDecodeError as e:
                error_response = {
                    "id": None,
                    "type": "error",
                    "error": "Invalid JSON format",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send(json.dumps(error_response))
                
            except Exception as e:
                logger.error(f"Error processing message from {client_id}: {e}")
                error_response = {
                    "id": data.get("id") if isinstance(data, dict) else None,
                    "type": "error",
                    "error": "Internal server error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send(json.dumps(error_response))
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.clients:
            return
            
        message_str = json.dumps(message)
        disconnected_clients = []
        
        for client_id, websocket in self.clients.items():
            try:
                await websocket.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def start_server(self):
        """Start the MCP WebSocket server."""
        self.running = True
        logger.info(f"Starting MCP server on {settings.mcp_host}:{settings.mcp_port}")
        
        async with websockets.serve(
            self.register_client,
            settings.mcp_host,
            settings.mcp_port,
            ping_interval=20,
            ping_timeout=10
        ):
            logger.info("MCP server started successfully")
            
            # Keep the server running
            while self.running:
                await asyncio.sleep(1)
    
    async def stop_server(self):
        """Stop the MCP server."""
        self.running = False
        logger.info("MCP server stopped")

# Global server instance
mcp_server = MCPServer()
```

### 3.2 Create core/message_handler.py

```python
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from agents.lead_processor import LeadProcessor
from agents.researcher import Researcher
from agents.persona_analyzer import PersonaAnalyzer
from agents.strategy_generator import StrategyGenerator
from agents.message_creator import MessageCreator
from services.business_context_service import BusinessContextService
from services.metrics_service import MetricsService
from utils.logger import get_logger

logger = get_logger(__name__)

class MessageHandler:
    def __init__(self):
        # Initialize agents
        self.lead_processor = LeadProcessor()
        self.researcher = Researcher()
        self.persona_analyzer = PersonaAnalyzer()
        self.strategy_generator = StrategyGenerator()
        self.message_creator = MessageCreator()
        
        # Initialize services
        self.business_context_service = BusinessContextService()
        self.metrics_service = MetricsService()
        
        # Message handlers mapping
        self.handlers = {
            # Agent Management
            "agent.start": self._handle_agent_start,
            "agent.stop": self._handle_agent_stop,
            "agent.status": self._handle_agent_status,
            "agent.update_metrics": self._handle_agent_update_metrics,
            
            # Lead Processing
            "lead.process": self._handle_lead_process,
            "lead.research": self._handle_lead_research,
            "lead.analyze_persona": self._handle_lead_analyze_persona,
            "lead.generate_strategy": self._handle_lead_generate_strategy,
            "lead.create_message": self._handle_lead_create_message,
            
            # Business Context
            "business_context.get": self._handle_business_context_get,
            "business_context.update": self._handle_business_context_update,
            
            # Chat
            "chat.send_message": self._handle_chat_send_message,
            
            # System
            "system.health": self._handle_system_health,
            "system.status": self._handle_system_status,
        }
    
    async def handle_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route and handle incoming messages."""
        message_type = data.get("type")
        message_id = data.get("id", str(uuid.uuid4()))
        
        if message_type not in self.handlers:
            return {
                "id": message_id,
                "type": "error",
                "error": "Unknown message type",
                "message": f"No handler for message type: {message_type}",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            handler = self.handlers[message_type]
            result = await handler(data)
            
            return {
                "id": message_id,
                "type": f"{message_type}.response",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling message {message_type}: {e}")
            return {
                "id": message_id,
                "type": "error",
                "error": "Handler execution failed",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Agent Management Handlers
    async def _handle_agent_start(self, data: Dict[str, Any]) -> Dict[str, Any]:
        agent_name = data.get("agent_name")
        # Implementation for starting an agent
        return {"status": "started", "agent_name": agent_name}
    
    async def _handle_agent_stop(self, data: Dict[str, Any]) -> Dict[str, Any]:
        agent_name = data.get("agent_name")
        # Implementation for stopping an agent
        return {"status": "stopped", "agent_name": agent_name}
    
    async def _handle_agent_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        agent_name = data.get("agent_name")
        # Implementation for getting agent status
        return await self.metrics_service.get_agent_status(agent_name)
    
    async def _handle_agent_update_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        agent_name = data.get("agent_name")
        metrics = data.get("metrics", {})
        # Implementation for updating agent metrics
        return await self.metrics_service.update_agent_metrics(agent_name, metrics)
    
    # Lead Processing Handlers
    async def _handle_lead_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        lead_data = data.get("lead_data")
        stage = data.get("stage", "intake")
        return await self.lead_processor.process_lead(lead_data, stage)
    
    async def _handle_lead_research(self, data: Dict[str, Any]) -> Dict[str, Any]:
        company_data = data.get("company_data")
        return await self.researcher.research_company(company_data)
    
    async def _handle_lead_analyze_persona(self, data: Dict[str, Any]) -> Dict[str, Any]:
        lead_data = data.get("lead_data")
        return await self.persona_analyzer.analyze_persona(lead_data)
    
    async def _handle_lead_generate_strategy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        lead_data = data.get("lead_data")
        business_context = data.get("business_context")
        return await self.strategy_generator.generate_strategy(lead_data, business_context)
    
    async def _handle_lead_create_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        lead_data = data.get("lead_data")
        strategy = data.get("strategy")
        return await self.message_creator.create_message(lead_data, strategy)
    
    # Business Context Handlers
    async def _handle_business_context_get(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.business_context_service.get_context()
    
    async def _handle_business_context_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        context_data = data.get("context_data")
        return await self.business_context_service.update_context(context_data)
    
    # Chat Handlers
    async def _handle_chat_send_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        agent_name = data.get("agent_name")
        message = data.get("message")
        # Implementation for chat message handling
        return {
            "agent_name": agent_name,
            "response": f"Agent {agent_name} received: {message}",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # System Handlers
    async def _handle_system_health(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": "00:00:00",  # Implement actual uptime tracking
            "memory_usage": "50%",  # Implement actual memory monitoring
            "cpu_usage": "25%"      # Implement actual CPU monitoring
        }
    
    async def _handle_system_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.metrics_service.get_system_status()
```

---

## 🤖 Step 4: Agent Implementations

### 4.1 Create agents/base_agent.py

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

from utils.logger import get_logger

logger = get_logger(__name__)

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.status = "idle"
        self.current_task = None
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_processing_time": 0.0,
            "success_rate": 0.0,
            "last_activity": None
        }
        self.created_at = datetime.utcnow()
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data and return results."""
        pass
    
    async def start_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start processing a task."""
        self.status = "processing"
        self.current_task = task_data
        start_time = datetime.utcnow()
        
        try:
            result = await self.process(task_data)
            
            # Update metrics on success
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics["tasks_completed"] += 1
            self._update_average_processing_time(processing_time)
            self._update_success_rate()
            self.metrics["last_activity"] = datetime.utcnow().isoformat()
            
            self.status = "idle"
            self.current_task = None
            
            logger.info(f"Agent {self.name} completed task in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            # Update metrics on failure
            self.metrics["tasks_failed"] += 1
            self._update_success_rate()
            self.metrics["last_activity"] = datetime.utcnow().isoformat()
            
            self.status = "error"
            self.current_task = None
            
            logger.error(f"Agent {self.name} failed task: {e}")
            raise
    
    def _update_average_processing_time(self, new_time: float):
        """Update the average processing time metric."""
        total_tasks = self.metrics["tasks_completed"]
        current_avg = self.metrics["average_processing_time"]
        
        # Calculate new average
        self.metrics["average_processing_time"] = (
            (current_avg * (total_tasks - 1) + new_time) / total_tasks
        )
    
    def _update_success_rate(self):
        """Update the success rate metric."""
        total_tasks = self.metrics["tasks_completed"] + self.metrics["tasks_failed"]
        if total_tasks > 0:
            self.metrics["success_rate"] = (
                self.metrics["tasks_completed"] / total_tasks
            ) * 100
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics."""
        return {
            "name": self.name,
            "status": self.status,
            "current_task": self.current_task,
            "metrics": self.metrics,
            "uptime": (datetime.utcnow() - self.created_at).total_seconds()
        }
```

### 4.2 Create agents/lead_processor.py

```python
from typing import Dict, Any
import asyncio

from agents.base_agent import BaseAgent
from utils.logger import get_logger

logger = get_logger(__name__)

class LeadProcessor(BaseAgent):
    def __init__(self):
        super().__init__("lead_processor")
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a lead through the specified stage."""
        lead_data = data.get("lead_data", {})
        stage = data.get("stage", "intake")
        
        logger.info(f"Processing lead {lead_data.get('company_name')} at stage {stage}")
        
        # Simulate processing time
        await asyncio.sleep(2)
        
        if stage == "intake":
            return await self._process_intake(lead_data)
        elif stage == "analysis":
            return await self._process_analysis(lead_data)
        elif stage == "persona":
            return await self._process_persona(lead_data)
        elif stage == "strategy":
            return await self._process_strategy(lead_data)
        elif stage == "message":
            return await self._process_message(lead_data)
        else:
            raise ValueError(f"Unknown processing stage: {stage}")
    
    async def _process_intake(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process lead at intake stage."""
        # Basic lead validation and scoring
        company_name = lead_data.get("company_name", "")
        website = lead_data.get("website", "")
        
        # Simulate AI-based initial scoring
        relevance_score = min(95, len(company_name) * 10 + 50)
        roi_potential = min(90, len(website) * 8 + 40)
        
        return {
            "stage": "analysis",
            "relevance_score": relevance_score,
            "roi_potential": roi_potential,
            "qualification_tier": "high" if relevance_score > 80 else "medium",
            "processing_notes": "Initial intake completed, ready for detailed analysis"
        }
    
    async def _process_analysis(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process lead at analysis stage."""
        # Detailed company analysis
        return {
            "stage": "persona",
            "brazilian_market_fit": 85,
            "sector_analysis": {
                "primary_sector": "Technology",
                "market_position": "Growth",
                "competitive_landscape": "Moderate"
            },
            "processing_notes": "Company analysis completed, proceeding to persona identification"
        }
    
    async def _process_persona(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process lead at persona stage."""
        # Identify decision makers and personas
        return {
            "stage": "strategy",
            "likely_contact_role": "CTO",
            "decision_maker_probability": 0.78,
            "persona_analysis": {
                "role": "Chief Technology Officer",
                "pain_points": ["Technical debt", "Scalability", "Team productivity"],
                "triggers": ["New technology adoption", "System modernization"]
            },
            "processing_notes": "Persona analysis completed, ready for strategy generation"
        }
    
    async def _process_strategy(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process lead at strategy stage."""
        # Generate outreach strategy
        return {
            "stage": "message",
            "outreach_strategy": {
                "approach": "Technical value proposition",
                "key_messages": ["Reduce technical debt", "Improve scalability"],
                "timing": "immediate",
                "channel": "email"
            },
            "processing_notes": "Strategy generated, ready for message creation"
        }
    
    async def _process_message(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process lead at message stage."""
        # Create personalized message
        company_name = lead_data.get("company_name", "")
        
        message = f"""Hi there,

I noticed {company_name} is growing rapidly in the technology sector. 

Based on my research, you might be facing challenges with technical debt and scalability as you expand. Our platform has helped similar companies reduce technical debt by 40% while improving team productivity.

Would you be interested in a brief conversation about how we've helped companies like yours overcome these challenges?

Best regards,
[Your Name]"""
        
        return {
            "stage": "completed",
            "generated_message": message,
            "message_metadata": {
                "tone": "professional",
                "length": "medium",
                "personalization_level": "high"
            },
            "processing_notes": "Lead processing completed successfully"
        }

    async def process_lead(self, lead_data: Dict[str, Any], stage: str) -> Dict[str, Any]:
        """Public method to process a lead."""
        return await self.start_task({
            "lead_data": lead_data,
            "stage": stage
        })
```

### 4.3 Create Additional Agent Files

Create the remaining agent files with similar structure:
- `agents/researcher.py`
- `agents/persona_analyzer.py`
- `agents/strategy_generator.py`
- `agents/message_creator.py`

---

## 🔧 Step 5: Services

### 5.1 Create services/business_context_service.py

```python
from typing import Dict, Any, Optional
import json
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)

class BusinessContextService:
    def __init__(self):
        self.context_data = {}
        self.last_updated = None
    
    async def get_context(self) -> Dict[str, Any]:
        """Get current business context."""
        return {
            "context": self.context_data,
            "last_updated": self.last_updated
        }
    
    async def update_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update business context."""
        self.context_data = context_data
        self.last_updated = datetime.utcnow().isoformat()
        
        logger.info("Business context updated")
        
        return {
            "status": "updated",
            "timestamp": self.last_updated
        }
```

---

## 🚀 Step 6: Main Application

### 6.1 Create main.py

```python
import asyncio
import signal
import sys
from dotenv import load_dotenv

from core.websocket_server import mcp_server
from utils.logger import setup_logging, get_logger

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = get_logger(__name__)

async def shutdown_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    await mcp_server.stop_server()
    sys.exit(0)

async def main():
    """Main application entry point."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(shutdown_handler(s, f)))
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown_handler(s, f)))
    
    try:
        logger.info("Starting Nellia MCP Server...")
        await mcp_server.start_server()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await mcp_server.stop_server()

if __name__ == "__main__":
    asyncio.run(main())
```

### 6.2 Create utils/logger.py

```python
import logging
import structlog
from config.settings import settings

def setup_logging():
    """Setup structured logging."""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper()),
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    """Get a structured logger instance."""
    return structlog.get_logger(name)
```

---

## 🧪 Step 7: Testing

### 7.1 Create test_mcp_server.py

```python
import asyncio
import websockets
import json
from datetime import datetime

async def test_mcp_connection():
    """Test basic MCP server connection and communication."""
    uri = "ws://localhost:8000"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to MCP server")
            
            # Test system health
            health_check = {
                "id": "test-1",
                "type": "system.health",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket.send(json.dumps(health_check))
            response = await websocket.recv()
            print(f"Health check response: {json.loads(response)}")
            
            # Test lead processing
            lead_test = {
                "id": "test-2",
                "type": "lead.process",
                "lead_data": {
                    "company_name": "Test Company",
                    "website": "https://testcompany.com"
                },
                "stage": "intake",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket.send(json.dumps(lead_test))
            response = await websocket.recv()
            print(f"Lead processing response: {json.loads(response)}")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
```

---

## 🚀 Step 8: Running the Server

### 8.1 Start the MCP Server

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Run the server
python main.py
```

### 8.2 Test the Connection

```bash
# In another terminal
python test_mcp_server.py
```

---

## 🔧 Step 9: Integration with NestJS Backend

Your NestJS backend is already configured to connect to this MCP server. The WebSocket connection should establish automatically when:

1. The MCP server is running on `localhost:8000`
2. The NestJS backend starts and the MCP service attempts connection
3. Both services should begin communicating using the message protocol defined

### 9.1 Verify Integration

1. Start the MCP server: `python main.py`
2. Start the NestJS backend: `cd backend && npm run start:dev`
3. Check logs for successful WebSocket connection
4. Test API endpoints in the backend that trigger MCP communication

---

## 📚 Next Steps

1. **Implement AI Integration**: Add actual AI providers (OpenAI, Anthropic) to the agents
2. **Add Research Capabilities**: Implement web scraping and API integrations
3. **Enhance Error Handling**: Add robust error handling and retry mechanisms
4. **Add Monitoring**: Implement health checks and performance monitoring
5. **Scale**: Add support for multiple concurrent processes and load balancing

---

## 🚨 Important Notes

- **Environment Variables**: Make sure to set all required API keys in your `.env` file
- **Dependencies**: Install all Python dependencies before running
- **Port Configuration**: Ensure port 8000 is available for the MCP server
- **Logging**: Check logs for connection and processing issues
- **Testing**: Use the provided test script to verify functionality

This implementation provides a solid foundation for your Python MCP server that integrates seamlessly with your NestJS backend!
