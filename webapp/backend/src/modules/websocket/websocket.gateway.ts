import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
  OnGatewayInit,
  MessageBody,
  ConnectedSocket,
} from '@nestjs/websockets';
import { Logger, UseGuards } from '@nestjs/common';
import { Server, Socket } from 'socket.io';
import { WebSocketService } from './websocket.service';
import {
  PingMessage,
  SubscribeToUpdatesMessage,
  UnsubscribeFromUpdatesMessage,
  RealTimeEntity,
  JoinUserRoomMessage,
} from './dto/websocket.dto';

@WebSocketGateway({
  cors: {
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    methods: ['GET', 'POST'],
    credentials: true,
  },
  transports: ['websocket', 'polling'],
})
export class NelliaWebSocketGateway implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  private readonly logger = new Logger(NelliaWebSocketGateway.name);
  private clientSubscriptions = new Map<string, Set<RealTimeEntity>>();

  constructor(private readonly webSocketService: WebSocketService) {}

  afterInit(server: Server) {
    this.webSocketService.setServer(server);
    this.logger.log('WebSocket Gateway initialized');

    // Set up periodic connection stats broadcast
    setInterval(() => {
      this.webSocketService.broadcastConnectionStats();
    }, 60000); // Every minute
  }

  handleConnection(client: Socket) {
    this.logger.log(`Client attempting to connect: ${client.id}`);
    
    try {
      // Initialize client subscriptions
      this.clientSubscriptions.set(client.id, new Set());
      
      // Handle connection via service
      this.webSocketService.handleConnection(client);
      
      this.logger.log(`Client successfully connected: ${client.id}`);
    } catch (error) {
      this.logger.error(`Error during client connection: ${error.message}`, error.stack);
      client.disconnect();
    }
  }

  handleDisconnect(client: Socket) {
    this.logger.log(`Client disconnecting: ${client.id}`);
    
    try {
      // Clean up client subscriptions
      this.clientSubscriptions.delete(client.id);
      
      // Handle disconnection via service
      this.webSocketService.handleDisconnection(client);
      
      this.logger.log(`Client successfully disconnected: ${client.id}`);
    } catch (error) {
      this.logger.error(`Error during client disconnection: ${error.message}`, error.stack);
    }
  }

  @SubscribeMessage('ping')
  handlePing(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: PingMessage,
  ): void {
    this.logger.debug(`Received ping from client: ${client.id}`);
    this.webSocketService.handlePing(client);
  }

  @SubscribeMessage('subscribe')
  handleSubscribe(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: SubscribeToUpdatesMessage,
  ): void {
    this.logger.debug(`Client ${client.id} subscribing to: ${data.entities.join(', ')}`);
    
    try {
      const clientSubs = this.clientSubscriptions.get(client.id) || new Set();
      
      data.entities.forEach(entity => {
        clientSubs.add(entity);
      });
      
      this.clientSubscriptions.set(client.id, clientSubs);
      
      // Confirm subscription
      client.emit('subscription-confirmed', {
        entities: data.entities,
        timestamp: new Date().toISOString(),
      });
      
      this.logger.log(`Client ${client.id} subscribed to: ${data.entities.join(', ')}`);
    } catch (error) {
      this.logger.error(`Error subscribing client ${client.id}:`, error);
      client.emit('subscription-error', {
        error: 'Failed to subscribe to updates',
        timestamp: new Date().toISOString(),
      });
    }
  }

  @SubscribeMessage('unsubscribe')
  handleUnsubscribe(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: UnsubscribeFromUpdatesMessage,
  ): void {
    this.logger.debug(`Client ${client.id} unsubscribing from: ${data.entities.join(', ')}`);
    
    try {
      const clientSubs = this.clientSubscriptions.get(client.id);
      
      if (clientSubs) {
        data.entities.forEach(entity => {
          clientSubs.delete(entity);
        });
      }
      
      // Confirm unsubscription
      client.emit('unsubscription-confirmed', {
        entities: data.entities,
        timestamp: new Date().toISOString(),
      });
      
      this.logger.log(`Client ${client.id} unsubscribed from: ${data.entities.join(', ')}`);
    } catch (error) {
      this.logger.error(`Error unsubscribing client ${client.id}:`, error);
    }
  }

  @SubscribeMessage('get-connection-stats')
  handleGetConnectionStats(@ConnectedSocket() client: Socket): void {
    const stats = this.webSocketService.getConnectionStats();
    client.emit('connection-stats', stats);
  }

  @SubscribeMessage('heartbeat')
  handleHeartbeat(@ConnectedSocket() client: Socket): void {
    client.emit('heartbeat-response', {
      timestamp: new Date().toISOString(),
      clientId: client.id,
    });
  }

  @SubscribeMessage('join-user-room')
  handleJoinUserRoom(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: JoinUserRoomMessage,
  ): void {
    this.logger.debug(`Client ${client.id} joining user room for user: ${data.userId}`);
    
    try {
      this.webSocketService.joinUserRoom(client, data.userId);
      this.logger.log(`Client ${client.id} successfully joined user room for user: ${data.userId}`);
    } catch (error) {
      this.logger.error(`Error joining user room for client ${client.id}:`, error);
      client.emit('user-room-join-error', {
        error: 'Failed to join user room',
        userId: data.userId,
        timestamp: new Date().toISOString(),
      });
    }
  }

  // Method to broadcast to subscribed clients only
  broadcastToSubscribers(entity: RealTimeEntity, event: string, data: any) {
    const subscribedClients = Array.from(this.clientSubscriptions.entries())
      .filter(([_, subscriptions]) => subscriptions.has(entity))
      .map(([clientId]) => clientId);

    subscribedClients.forEach(clientId => {
      this.webSocketService.sendToClient(clientId, event, data);
    });

    this.logger.debug(`Broadcasted ${event} to ${subscribedClients.length} subscribed clients`);
  }

  // Health check endpoint for gateway
  getHealthStatus() {
    return {
      gateway: 'healthy',
      connections: this.clientSubscriptions.size,
      subscriptions: Array.from(this.clientSubscriptions.values())
        .reduce((total, subs) => total + subs.size, 0),
      timestamp: new Date().toISOString(),
    };
  }
}
