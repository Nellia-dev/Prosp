import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from './AuthContext';
import { useToast } from '../hooks/use-toast';

interface SubscribeFunction {
  <T>(event: string, callback: (data: T) => void): () => void;
}

interface WebSocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  connect: () => void;
  disconnect: () => void;
  emit: (event: string, data?: unknown) => void;
  subscribe: SubscribeFunction;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const { user, token } = useAuth();
  const { toast } = useToast();

  // Effect for connection management
  useEffect(() => {
    if (user && token) {
      const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:3001';
      const newSocket = io(wsUrl, {
        auth: { token },
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 10000,
      });

      setSocket(newSocket);
      setConnectionStatus('connecting');

      newSocket.on('connect', () => {
        console.log('WebSocket connected:', newSocket.id);
        setConnectionStatus('connected');
        toast({
          title: "Connected",
          description: "Real-time updates enabled",
          duration: 2000,
        });
      });

      newSocket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);
        setConnectionStatus('disconnected');
        if (reason !== 'io client disconnect') {
          toast({
            title: "Connection Lost",
            description: "Attempting to reconnect...",
            variant: "destructive",
          });
        }
      });

      newSocket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error.message);
        setConnectionStatus('error');
      });

      newSocket.on('unauthorized', (error) => {
        console.error('WebSocket authentication error:', error);
        setConnectionStatus('error');
        toast({
          title: "Authentication Error",
          description: "Please refresh and log in again",
          variant: "destructive",
        });
        newSocket.disconnect();
      });

      return () => {
        newSocket.disconnect();
        setSocket(null);
        setConnectionStatus('disconnected');
      };
    }
  }, [user, token, toast]);

  const connect = useCallback(() => {
    socket?.connect();
  }, [socket]);

  const disconnect = useCallback(() => {
    socket?.disconnect();
  }, [socket]);

  const emit = useCallback((event: string, data?: unknown) => {
    if (socket?.connected) {
      socket.emit(event, data);
    }
  }, [socket]);

  const subscribe = useCallback(<T,>(event: string, callback: (data: T) => void) => {
    if (socket) {
      const handler = (data: unknown) => callback(data as T);
      socket.on(event, handler);
      
      return () => {
        socket.off(event, handler);
      };
    }
    return () => {}; // No-op if no socket
  }, [socket]);

  // Handle window focus for reconnection
  useEffect(() => {
    const handleFocus = () => {
      if (socket && !socket.connected) {
        connect();
      }
    };
    window.addEventListener('focus', handleFocus);
    return () => {
      window.removeEventListener('focus', handleFocus);
    };
  }, [socket, connect]);

  const value: WebSocketContextType = {
    socket,
    isConnected: connectionStatus === 'connected',
    connectionStatus,
    connect,
    disconnect,
    emit,
    subscribe,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

export default WebSocketContext;
