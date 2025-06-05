import { Injectable, Logger } from '@nestjs/common';
import { Server, Socket } from 'socket.io';
import { WebSocketMessage, WebSocketMessageType, RealTimeUpdate } from './dto/websocket.dto';

@Injectable()
export class WebSocketService {
  private readonly logger = new Logger(WebSocketService.name);
  private server: Server;
  private connectedClients = new Map<string, Socket>();

  setServer(server: Server) {
    this.server = server;
  }

  handleConnection(client: Socket) {
    this.logger.log(`Client connected: ${client.id}`);
    this.connectedClients.set(client.id, client);
    
    // Send initial connection confirmation
    client.emit('connection-confirmed', {
      clientId: client.id,
      timestamp: new Date().toISOString(),
    });
  }

  handleDisconnection(client: Socket) {
    this.logger.log(`Client disconnected: ${client.id}`);
    this.connectedClients.delete(client.id);
  }

  handlePing(client: Socket) {
    client.emit('pong', { timestamp: new Date().toISOString() });
  }

  // Broadcast methods for different types of updates
  broadcastAgentStatusUpdate(agentData: any) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.AGENT_STATUS_UPDATE,
      data: agentData,
      timestamp: new Date().toISOString(),
    };
    
    this.broadcast('agent-status-update', message);
    this.logger.debug(`Broadcasted agent status update for agent: ${agentData.id}`);
  }

  broadcastLeadUpdate(leadData: any) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.LEAD_UPDATE,
      data: leadData,
      timestamp: new Date().toISOString(),
    };
    
    this.broadcast('lead-update', message);
    this.logger.debug(`Broadcasted lead update for lead: ${leadData.id}`);
  }

  broadcastMetricsUpdate(metricsData: any) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.METRICS_UPDATE,
      data: metricsData,
      timestamp: new Date().toISOString(),
    };
    
    this.broadcast('metrics-update', message);
    this.logger.debug('Broadcasted metrics update');
  }

  broadcastProcessingProgress(progressData: any) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.PROCESSING_PROGRESS,
      data: progressData,
      timestamp: new Date().toISOString(),
    };
    
    this.broadcast('processing-progress', message);
    this.logger.debug(`Broadcasted processing progress for lead: ${progressData.lead_id}`);
  }

  // Real-time update broadcasting
  broadcastRealTimeUpdate(update: RealTimeUpdate) {
    this.broadcast('real-time-update', update);
    this.logger.debug(`Broadcasted real-time update: ${update.entity} ${update.action}`);
  }

  // Send message to specific client
  sendToClient(clientId: string, event: string, data: any) {
    const client = this.connectedClients.get(clientId);
    if (client) {
      client.emit(event, data);
      this.logger.debug(`Sent ${event} to client ${clientId}`);
    } else {
      this.logger.warn(`Client ${clientId} not found`);
    }
  }

  // Broadcast to all connected clients
  private broadcast(event: string, data: any) {
    if (!this.server) {
      this.logger.warn('WebSocket server not initialized');
      return;
    }

    this.server.emit(event, data);
    this.logger.debug(`Broadcasted ${event} to ${this.connectedClients.size} clients`);
  }

  // Get connection statistics
  getConnectionStats() {
    return {
      totalConnections: this.connectedClients.size,
      clientIds: Array.from(this.connectedClients.keys()),
      timestamp: new Date().toISOString(),
    };
  }

  // Broadcast connection stats periodically
  broadcastConnectionStats() {
    const stats = this.getConnectionStats();
    this.broadcast('connection-stats', stats);
  }

  // Health check for WebSocket service
  isHealthy(): boolean {
    return this.server !== undefined;
  }
}