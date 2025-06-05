import { Module, Global } from '@nestjs/common';
import { NelliaWebSocketGateway } from './websocket.gateway';
import { WebSocketService } from './websocket.service';
import { WebSocketEventsService } from './websocket-events.service';

@Global()
@Module({
  providers: [
    NelliaWebSocketGateway,
    WebSocketService,
    WebSocketEventsService,
  ],
  exports: [
    WebSocketService,
    WebSocketEventsService,
    NelliaWebSocketGateway,
  ],
})
export class WebSocketModule {}