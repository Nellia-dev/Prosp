import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from './AuthContext';
import { useToast } from '../hooks/use-toast';

interface WebSocketEventData {
  [key: string]: unknown;
}

interface WebSocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  connect: () => void;
  disconnect: () => void;
  emit: (event: string, data?: WebSocketEventData) => void;
  subscribe: (event: string, callback: (data: WebSocketEventData) => void) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  
  const { user, token } = useAuth();
  const { toast } = useToast();

  const maxReconnectAttempts = 5;
  const reconnectDelay = (attempt: number) => Math.min(1000 * Math.pow(2, attempt), 30000); // Exponential backoff, max 30s

  const connect = useCallback(() => {
    if (socket?.connected) return;
    
    if (!token) {
      console.log('WebSocket: No token available, skipping connection');
      return;
    }

    setConnectionStatus('connecting');
    
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:3001';
    
    const newSocket = io(wsUrl, {
      auth: {
        token: token
      },
      transports: ['websocket', 'polling'],
      timeout: 10000,
      reconnection: false, // We'll handle reconnection manually
    });

    // Connection handlers
    newSocket.on('connect', () => {
      console.log('WebSocket connected:', newSocket.id);
      setIsConnected(true);
      setConnectionStatus('connected');
      setReconnectAttempts(0);
      
      toast({
        title: "Connected",
        description: "Real-time updates enabled",
        duration: 2000,
      });
    });

    newSocket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      setIsConnected(false);
      setConnectionStatus('disconnected');
      
      // Auto-reconnect on unexpected disconnections
      if (reason === 'io server disconnect') {
        // Server initiated disconnect, don't reconnect
        toast({
          title: "Disconnected",
          description: "Connection closed by server",
          variant: "destructive",
        });
      } else {
        // Client side disconnect or network issue, attempt reconnect
        setTimeout(() => {
          if (reconnectAttempts < maxReconnectAttempts) {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }
        }, reconnectDelay(reconnectAttempts));
      }
    });

    newSocket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setConnectionStatus('error');
      
      if (reconnectAttempts < maxReconnectAttempts) {
        setTimeout(() => {
          setReconnectAttempts(prev => prev + 1);
          connect();
        }, reconnectDelay(reconnectAttempts));
      } else {
        toast({
          title: "Connection Failed",
          description: "Unable to establish real-time connection",
          variant: "destructive",
        });
      }
    });

    // Authentication error
    newSocket.on('unauthorized', (error) => {
      console.error('WebSocket authentication error:', error);
      setConnectionStatus('error');
      toast({
        title: "Authentication Error",
        description: "Please refresh and log in again",
        variant: "destructive",
      });
    });

    setSocket(newSocket);
  }, [token, reconnectAttempts, toast]);

  const disconnect = useCallback(() => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
      setIsConnected(false);
      setConnectionStatus('disconnected');
      setReconnectAttempts(0);
    }
  }, [socket]);

  const emit = useCallback((event: string, data?: WebSocketEventData) => {
    if (socket?.connected) {
      socket.emit(event, data);
    }
  }, [socket]);

  const subscribe = useCallback((event: string, callback: (data: WebSocketEventData) => void) => {
    if (socket) {
      socket.on(event, callback);
      
      // Return unsubscribe function
      return () => {
        socket.off(event, callback);
      };
    }
    
    return () => {}; // No-op if no socket
  }, [socket]);

  // Connect when user is authenticated
  useEffect(() => {
    if (user && token) {
      connect();
    } else {
      disconnect();
    }

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [user, token, connect, disconnect]);

  // Handle window focus/blur for connection management
  useEffect(() => {
    const handleFocus = () => {
      if (user && token && !socket?.connected) {
        connect();
      }
    };

    const handleBlur = () => {
      // Keep connection alive on blur, just reduce activity
    };

    window.addEventListener('focus', handleFocus);
    window.addEventListener('blur', handleBlur);

    return () => {
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('blur', handleBlur);
    };
  }, [user, token, socket, connect]);

  const value: WebSocketContextType = {
    socket,
    isConnected,
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
