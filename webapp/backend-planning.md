## __Nellia Prospector Backend - Development Plan__

### __1. System Architecture Overview__

### __2. Core Data Models Required (Based on Frontend Analysis)__

From analyzing your frontend, I identified these critical data entities:

__Agent Management:__

- AgentStatus tracking with metrics
- Real-time agent performance monitoring
- Task queue management

__Lead Processing:__

- Lead lifecycle from intake to completion
- Processing stage tracking (intake → analysis → persona → strategy → message → completed)
- Scoring systems (relevance, ROI potential, Brazilian market fit)
- Qualification tiers

__Business Context:__

- Configurable business parameters
- Industry focus areas
- Pain points and value propositions

__Chat System:__

- Multi-agent communication
- Message history per agent
- File attachments support

__Real-time Updates:__

- Live agent status updates
- Processing progress tracking
- Metrics visualization data

### __3. Project Structure Plan__

```javascript
backend/
├── src/
│   ├── main.ts
│   ├── app.module.ts
│   ├── config/
│   │   ├── database.config.ts
│   │   ├── redis.config.ts
│   │   └── mcp.config.ts
│   ├── common/
│   │   ├── decorators/
│   │   ├── filters/
│   │   ├── guards/
│   │   ├── interceptors/
│   │   └── pipes/
│   ├── modules/
│   │   ├── agents/
│   │   ├── leads/
│   │   ├── business-context/
│   │   ├── chat/
│   │   ├── metrics/
│   │   ├── auth/
│   │   └── mcp/
│   ├── database/
│   │   ├── entities/
│   │   ├── migrations/
│   │   └── seeders/
│   └── shared/
│       ├── dto/
│       ├── interfaces/
│       └── types/
├── test/
├── docker-compose.yml
├── Dockerfile
├── package.json
└── README.md
```

### __4. Key API Endpoints Plan__

__Agent Management:__

- `GET /api/agents` - List all agents with status
- `GET /api/agents/:id` - Get specific agent details
- `POST /api/agents/:id/start` - Start an agent
- `POST /api/agents/:id/stop` - Stop an agent
- `GET /api/agents/:id/metrics` - Get agent performance metrics

__Lead Management:__

- `GET /api/leads` - List leads with filtering/pagination
- `POST /api/leads` - Create new lead
- `GET /api/leads/:id` - Get lead details
- `PUT /api/leads/:id` - Update lead
- `DELETE /api/leads/:id` - Delete lead
- `POST /api/leads/:id/process` - Start lead processing
- `GET /api/leads/:id/progress` - Get processing progress

__Business Context:__

- `GET /api/business-context` - Get current business context
- `PUT /api/business-context` - Update business context

__Chat System:__

- `GET /api/chat/agents` - List available chat agents
- `GET /api/chat/:agentId/messages` - Get message history
- `POST /api/chat/:agentId/messages` - Send message to agent

__Metrics & Analytics:__

- `GET /api/metrics/overview` - Dashboard overview metrics
- `GET /api/metrics/performance` - Performance data for charts
- `GET /api/metrics/agents` - Agent-specific metrics

### __5. Technology Stack__

__Core Framework:__

- NestJS with TypeScript
- Express.js underlying server

__Database:__

- PostgreSQL for main data storage
- TypeORM for database operations
- Redis for caching and session storage

__Real-time Communication:__

- Socket.IO for WebSocket connections
- Bull Queue for job processing

__MCP Integration:__

- Custom MCP client service
- JSON-RPC communication with Python agents

__Additional Tools:__

- Swagger for API documentation
- Jest for testing
- Docker for containerization
- Helmet for security
- Rate limiting middleware

### __6. Implementation Phases__

__Phase 1: Core Infrastructure (Week 1)__

- Project setup with NestJS CLI
- Database configuration and basic entities
- MCP client service foundation
- Basic authentication setup

__Phase 2: Agent Management (Week 2)__

- Agent status tracking
- MCP communication layer
- Real-time agent monitoring
- WebSocket setup for live updates

__Phase 3: Lead Processing System (Week 3)__

- Lead CRUD operations
- Processing pipeline integration
- Stage tracking and progress monitoring
- File upload handling

__Phase 4: Business Context & Chat (Week 4)__

- Business context management
- Chat system with multi-agent support
- Message history and attachments
- Integration testing

__Phase 5: Metrics & Optimization (Week 5)__

- Dashboard metrics APIs
- Performance monitoring
- Caching optimization
- Load testing and scaling

### __7. Critical Integration Points__

__MCP Server Communication:__

- Establish secure connection to Python MCP server
- Handle agent lifecycle management
- Process lead data through agent pipeline
- Manage real-time status updates

__Real-time Updates:__

- WebSocket connections for live agent status
- Progress updates during lead processing
- Instant chat message delivery
- Metrics refresh for dashboard

__Data Synchronization:__

- Ensure consistency between frontend state and backend
- Handle offline scenarios gracefully
- Implement proper error recovery

### __8. Security Considerations__

- JWT-based authentication
- Rate limiting for API endpoints
- Input validation and sanitization
- Secure MCP communication
- File upload restrictions
- CORS configuration

### __9. Performance Optimizations__

- Redis caching for frequently accessed data
- Database query optimization
- Connection pooling
- Background job processing for heavy operations
- Pagination for large datasets
