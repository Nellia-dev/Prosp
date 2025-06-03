#!/usr/bin/env node

/**
 * Mock MCP Server for Nellia Prospector Backend Development
 *
 * This is a simple WebSocket server that simulates the Python MCP agent system
 * for testing and development purposes.
 */

const WebSocket = require("ws");
const http = require("http");

// Mock data for responses
const mockAgents = {
  "data-collector": {
    id: "data-collector",
    name: "data-collector",
    status: "active",
    metrics: {
      processingTime: 2.5,
      successRate: 0.94,
      queueDepth: 5,
      throughput: 12.3,
      tokenUsage: { used: 1200, limit: 10000 },
    },
    task: "Processing company data from LinkedIn",
  },
  "market-analyzer": {
    id: "market-analyzer",
    name: "market-analyzer",
    status: "active",
    metrics: {
      processingTime: 3.8,
      successRate: 0.89,
      queueDepth: 3,
      throughput: 8.7,
      tokenUsage: { used: 800, limit: 10000 },
    },
    task: "Analyzing market fit for TechCorp",
  },
  "persona-builder": {
    id: "persona-builder",
    name: "persona-builder",
    status: "idle",
    metrics: {
      processingTime: 4.2,
      successRate: 0.92,
      queueDepth: 0,
      throughput: 6.1,
      tokenUsage: { used: 400, limit: 10000 },
    },
    task: null,
  },
};

const mockBusinessContext = {
  description: "AI-powered sales automation platform",
  targetMarket: "B2B SaaS companies",
  valueProposition: "Increase sales efficiency by 300%",
  idealCustomer: "Sales teams of 10-50 people",
  painPoints: ["Manual prospecting", "Low conversion rates"],
  industryFocus: ["Technology", "Financial Services"],
};

// Create HTTP server for health checks
const server = http.createServer((req, res) => {
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(
    JSON.stringify({
      status: "healthy",
      timestamp: new Date().toISOString(),
      agents: Object.keys(mockAgents).length,
    })
  );
});

// Create WebSocket server
const wss = new WebSocket.Server({
  server,
  path: "/ws",
});

console.log("🤖 Mock MCP Server starting...");

// Helper function to generate request ID
function generateId() {
  return Math.random().toString(36).substr(2, 9);
}

// Helper function to simulate processing delay
function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

wss.on("connection", (ws) => {
  console.log("📡 Client connected to Mock MCP Server");

  // Send welcome message
  ws.send(
    JSON.stringify({
      type: "connection",
      status: "connected",
      timestamp: new Date().toISOString(),
      agents: Object.keys(mockAgents),
    })
  );

  // Handle incoming messages
  ws.on("message", async (data) => {
    try {
      const message = JSON.parse(data.toString());
      console.log("📥 Received:", message.type, message.requestId);

      // Simulate processing delay
      await delay(100 + Math.random() * 500);

      let response = {
        requestId: message.requestId,
        timestamp: new Date().toISOString(),
      };

      switch (message.type) {
        case "ping":
          response = {
            ...response,
            type: "pong",
            success: true,
          };
          break;

        case "agent.list":
          response = {
            ...response,
            type: "agent.list.response",
            success: true,
            data: Object.values(mockAgents),
          };
          break;

        case "agent.start":
          const agentId = message.agentId;
          if (mockAgents[agentId]) {
            mockAgents[agentId].status = "active";
            mockAgents[agentId].task =
              `Processing new tasks - started at ${new Date().toLocaleTimeString()}`;
            response = {
              ...response,
              type: "agent.start.response",
              success: true,
              data: mockAgents[agentId],
            };
          } else {
            response = {
              ...response,
              type: "agent.start.response",
              success: false,
              error: `Agent ${agentId} not found`,
            };
          }
          break;

        case "agent.stop":
          const stopAgentId = message.agentId;
          if (mockAgents[stopAgentId]) {
            mockAgents[stopAgentId].status = "idle";
            mockAgents[stopAgentId].task = null;
            response = {
              ...response,
              type: "agent.stop.response",
              success: true,
              data: mockAgents[stopAgentId],
            };
          } else {
            response = {
              ...response,
              type: "agent.stop.response",
              success: false,
              error: `Agent ${stopAgentId} not found`,
            };
          }
          break;

        case "agent.status":
          const statusAgentId = message.agentId;
          if (mockAgents[statusAgentId]) {
            response = {
              ...response,
              type: "agent.status.response",
              success: true,
              data: mockAgents[statusAgentId],
            };
          } else {
            response = {
              ...response,
              type: "agent.status.response",
              success: false,
              error: `Agent ${statusAgentId} not found`,
            };
          }
          break;

        case "lead.process":
          const leadData = message.leadData;
          // Simulate lead processing
          const processedLead = {
            ...leadData,
            processingStage: "analysis",
            scores: {
              relevance: Math.random() * 100,
              roiPotential: Math.random() * 100,
              brazilianMarketFit: Math.random() * 100,
            },
            qualificationTier: ["hot", "warm", "cold"][
              Math.floor(Math.random() * 3)
            ],
            processedAt: new Date().toISOString(),
          };

          response = {
            ...response,
            type: "lead.process.response",
            success: true,
            data: processedLead,
          };
          break;

        case "chat.send":
          const { agentId: chatAgentId, message: chatMessage } = message;
          // Simulate agent response
          const agentResponses = [
            `I understand you're asking about ${chatMessage.substring(0, 20)}... Let me help with that.`,
            `Based on our current analysis, I can provide insights on this topic.`,
            `That's an interesting question. Here's what I found in our data...`,
            `I'm processing this request and will have results shortly.`,
            `Let me analyze the current lead data to answer your question.`,
          ];

          response = {
            ...response,
            type: "chat.send.response",
            success: true,
            data: {
              agentId: chatAgentId,
              message:
                agentResponses[
                  Math.floor(Math.random() * agentResponses.length)
                ],
              timestamp: new Date().toISOString(),
            },
          };
          break;

        case "business-context.update":
          // Simulate updating business context
          response = {
            ...response,
            type: "business-context.update.response",
            success: true,
            data: {
              ...mockBusinessContext,
              ...message.context,
              updatedAt: new Date().toISOString(),
            },
          };
          break;

        case "business-context.get":
          response = {
            ...response,
            type: "business-context.get.response",
            success: true,
            data: mockBusinessContext,
          };
          break;

        case "system.status":
          response = {
            ...response,
            type: "system.status.response",
            success: true,
            data: {
              status: "healthy",
              uptime: process.uptime(),
              agents: Object.values(mockAgents).map((agent) => ({
                id: agent.id,
                status: agent.status,
                lastActivity: new Date().toISOString(),
              })),
              memory: process.memoryUsage(),
              timestamp: new Date().toISOString(),
            },
          };
          break;

        default:
          response = {
            ...response,
            type: "error",
            success: false,
            error: `Unknown message type: ${message.type}`,
          };
          break;
      }

      console.log("📤 Sending:", response.type, response.requestId);
      ws.send(JSON.stringify(response));
    } catch (error) {
      console.error("❌ Error processing message:", error);
      ws.send(
        JSON.stringify({
          type: "error",
          success: false,
          error: error.message,
          timestamp: new Date().toISOString(),
        })
      );
    }
  });

  // Handle connection close
  ws.on("close", () => {
    console.log("📡 Client disconnected from Mock MCP Server");
  });

  // Handle errors
  ws.on("error", (error) => {
    console.error("❌ WebSocket error:", error);
  });

  // Send periodic agent updates
  const updateInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      // Randomly update agent metrics
      Object.values(mockAgents).forEach((agent) => {
        if (agent.status === "active") {
          agent.metrics.processingTime += (Math.random() - 0.5) * 0.1;
          agent.metrics.queueDepth = Math.max(
            0,
            agent.metrics.queueDepth + Math.floor(Math.random() * 3) - 1
          );
          agent.metrics.throughput += (Math.random() - 0.5) * 0.5;
          agent.metrics.tokenUsage.used += Math.floor(Math.random() * 10);
        }
      });

      ws.send(
        JSON.stringify({
          type: "agent.metrics.update",
          timestamp: new Date().toISOString(),
          data: Object.values(mockAgents),
        })
      );
    }
  }, 5000);

  // Clean up interval on close
  ws.on("close", () => {
    clearInterval(updateInterval);
  });
});

const PORT = process.env.MCP_PORT || 8000;

server.listen(PORT, () => {
  console.log(`🚀 Mock MCP Server running on port ${PORT}`);
  console.log(`   HTTP Health Check: http://localhost:${PORT}`);
  console.log(`   WebSocket Endpoint: ws://localhost:${PORT}/ws`);
  console.log("");
  console.log("📋 Available message types:");
  console.log("   - ping");
  console.log("   - agent.list, agent.start, agent.stop, agent.status");
  console.log("   - lead.process");
  console.log("   - chat.send");
  console.log("   - business-context.get, business-context.update");
  console.log("   - system.status");
  console.log("");
  console.log("🛑 Press Ctrl+C to stop the server");
});

// Graceful shutdown
process.on("SIGINT", () => {
  console.log("\n🛑 Shutting down Mock MCP Server...");
  server.close(() => {
    console.log("✅ Mock MCP Server stopped");
    process.exit(0);
  });
});

process.on("SIGTERM", () => {
  console.log("\n🛑 Received SIGTERM, shutting down gracefully...");
  server.close(() => {
    console.log("✅ Mock MCP Server stopped");
    process.exit(0);
  });
});
