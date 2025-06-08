import { Injectable, Logger } from '@nestjs/common';
import { Server, Socket } from 'socket.io';
import { 
  WebSocketMessage, 
  WebSocketMessageType, 
  RealTimeUpdate,
  QuotaUpdateData,
  JobProgressData,
  JobCompletedData,
  JobFailedData,
  LeadUpdateData
} from './dto/websocket.dto';

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

  // User-specific room management
  joinUserRoom(client: Socket, userId: string) {
    const roomName = `user-${userId}`;
    client.join(roomName);
    this.logger.debug(`Client ${client.id} joined user room: ${roomName}`);
    
    // Confirm room join
    client.emit('user-room-joined', {
      userId,
      roomName,
      timestamp: new Date().toISOString(),
    });
  }

  leaveUserRoom(client: Socket, userId: string) {
    const roomName = `user-${userId}`;
    client.leave(roomName);
    this.logger.debug(`Client ${client.id} left user room: ${roomName}`);
  }

  // Send message to specific user room
  sendToUserRoom(userId: string, event: string, data: any) {
    if (!this.server) {
      this.logger.warn('WebSocket server not initialized');
      return;
    }

    const roomName = `user-${userId}`;
    this.server.to(roomName).emit(event, data);
    this.logger.debug(`Sent ${event} to user room: ${roomName}`);
  }

  emitToUser(userId: string, event: string, data: any) {
    this.sendToUserRoom(userId, event, data);
  }

  // New methods for quota and job updates
  emitQuotaUpdate(userId: string, quotaData: QuotaUpdateData) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.QUOTA_UPDATE,
      data: quotaData,
      timestamp: new Date().toISOString(),
    };
    
    this.sendToUserRoom(userId, 'quota-updated', message);
    this.logger.debug(`Sent quota update to user: ${userId}`);
  }

  emitJobProgress(userId: string, progressData: JobProgressData) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.JOB_PROGRESS,
      data: progressData,
      timestamp: new Date().toISOString(),
    };
    
    this.sendToUserRoom(userId, 'job-progress', message);
    this.logger.debug(`Sent job progress to user: ${userId}, job: ${progressData.jobId}`);
  }

  emitJobCompleted(userId: string, completedData: JobCompletedData) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.JOB_COMPLETED,
      data: completedData,
      timestamp: new Date().toISOString(),
    };
    
    this.sendToUserRoom(userId, 'job-completed', message);
    this.logger.debug(`Sent job completed to user: ${userId}, job: ${completedData.jobId}`);
    
    // Also emit quota update if included
    if (completedData.quotaUpdate) {
      this.emitQuotaUpdate(userId, completedData.quotaUpdate);
    }
  }

  emitJobFailed(userId: string, failedData: JobFailedData) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.JOB_FAILED,
      data: failedData,
      timestamp: new Date().toISOString(),
    };
    
    this.sendToUserRoom(userId, 'job-failed', message);
    this.logger.debug(`Sent job failed to user: ${userId}, job: ${failedData.jobId}`);
  }

  // Health check for WebSocket service
  isHealthy(): boolean {
    return this.server !== undefined;
  }

  emitLeadUpdate(userId: string, leadData: Partial<LeadUpdateData> & { id: string }) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.LEAD_UPDATE,
      data: leadData,
      timestamp: new Date().toISOString(),
    };
    this.sendToUserRoom(userId, 'lead-update', message);
    this.logger.debug(`Sent lead update to user ${userId} for lead ${leadData.id}`);
  }

  emitEnrichmentUpdate(userId: string, event: any) {
    const message: WebSocketMessage = {
      type: WebSocketMessageType.ENRICHMENT_UPDATE,
      data: event,
      timestamp: new Date().toISOString(),
    };
    this.sendToUserRoom(userId, 'enrichment-update', message);
    this.logger.debug(`Sent enrichment update to user ${userId} for job ${event.job_id}`);
  }
}
