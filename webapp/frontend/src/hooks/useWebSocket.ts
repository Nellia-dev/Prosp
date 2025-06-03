import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '../contexts/AuthContext';
import { API_CONFIG } from '../config/api';
import { AgentStatus, LeadData } from '../types/nellia';

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  reconnectAttempts: number;
}

export interface UseWebSocketOptions {
  autoConnect?: boolean;
  reconnectEnabled?: boolean;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
}

export interface NotificationData {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

export interface MetricsUpdateData {
  agentMetrics?: Record<string, unknown>;
  dashboardMetrics?: Record<string, unknown>;
  performanceData?: Record<string, unknown>;
}

export interface WebSocketEventHandlers {
  onAgentStatusUpdate?: (agentId: string, status: Partial<AgentStatus>) => void;
  onLeadUpdate?: (leadId: string, data: Partial<LeadData>) => void;
  onMetricsUpdate?: (metrics: MetricsUpdateData) => void;
  onNotification?: (notification: NotificationData) => void;
  onConnect?: () => void;
  onDisconnect?: (reason: string) => void;
  onError?: (error: Error) => void;
}

export const useWebSocket = (
  options: UseWebSocketOptions = {},
  eventHandlers: WebSocketEventHandlers = {}
) => {
  const { token, isAuthenticated } = useAuth();
  const socketRef = useRef<Socket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    reconnectAttempts: 0,
  });

  const {
    autoConnect = true,
    reconnectEnabled = true,
    maxReconnectAttempts = 5,
    reconnectDelay = 1000,
  } = options;

  const {
    onAgentStatusUpdate,
    onLeadUpdate,
    onMetricsUpdate,
    onNotification,
    onConnect,
    onDisconnect,
    onError,
  } = eventHandlers;

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (!reconnectEnabled || state.reconnectAttempts >= maxReconnectAttempts) {
      return;
    }

    clearReconnectTimeout();
    
    const delay = Math.min(reconnectDelay * Math.pow(2, state.reconnectAttempts), 30000);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      setState(prev => ({
        ...prev,
        reconnectAttempts: prev.reconnectAttempts + 1,
        isConnecting: true,
        error: null,
      }));
      connect();
    }, delay);
  }, [state.reconnectAttempts, maxReconnectAttempts, reconnectDelay, reconnectEnabled, clearReconnectTimeout]);

  const connect = useCallback(() => {
    if (!isAuthenticated || !token) {
      setState(prev => ({
        ...prev,
        isConnecting: false,
        error: 'Not authenticated',
      }));
      return;
    }

    if (socketRef.current?.connected) {
      return;
    }

    setState(prev => ({ ...prev, isConnecting: true, error: null }));

    try {
      const wsUrl = API_CONFIG.WS_URL;
      
      socketRef.current = io(wsUrl, {
        auth: {
          token: token,
        },
        transports: ['websocket'],
        reconnection: false, // We handle reconnection manually
      });

      const socket = socketRef.current;

      // Connection events
      socket.on('connect', () => {
        setState(prev => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          error: null,
          reconnectAttempts: 0,
        }));
        clearReconnectTimeout();
        onConnect?.();
      });

      socket.on('disconnect', (reason) => {
        setState(prev => ({
          ...prev,
          isConnected: false,
          isConnecting: false,
          error: `Disconnected: ${reason}`,
        }));
        onDisconnect?.(reason);
        
        // Schedule reconnect if it wasn't a manual disconnect
        if (reason !== 'io client disconnect') {
          scheduleReconnect();
        }
      });

      socket.on('connect_error', (error) => {
        setState(prev => ({
          ...prev,
          isConnected: false,
          isConnecting: false,
          error: `Connection error: ${error.message}`,
        }));
        onError?.(error);
        scheduleReconnect();
      });

      // Data events
      socket.on('agent:status_update', (data) => {
        onAgentStatusUpdate?.(data.agentId, data.status);
      });

      socket.on('lead:update', (data) => {
        onLeadUpdate?.(data.leadId, data.data);
      });

      socket.on('metrics:update', (data) => {
        onMetricsUpdate?.(data);
      });

      socket.on('notification', (data) => {
        onNotification?.(data);
      });

    } catch (error) {
      setState(prev => ({
        ...prev,
        isConnecting: false,
        error: `Failed to connect: ${error}`,
      }));
      onError?.(error);
    }
  }, [isAuthenticated, token, onConnect, onDisconnect, onError, onAgentStatusUpdate, onLeadUpdate, onMetricsUpdate, onNotification, clearReconnectTimeout, scheduleReconnect]);

  const disconnect = useCallback(() => {
    clearReconnectTimeout();
    
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }

    setState({
      isConnected: false,
      isConnecting: false,
      error: null,
      reconnectAttempts: 0,
    });
  }, [clearReconnectTimeout]);

  const emit = useCallback((event: string, data?: unknown) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
      return true;
    }
    return false;
  }, []);

  // Auto-connect on mount if authenticated
  useEffect(() => {
    if (autoConnect && isAuthenticated && token) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, isAuthenticated, token, connect, disconnect]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      clearReconnectTimeout();
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [clearReconnectTimeout]);

  return {
    ...state,
    connect,
    disconnect,
    emit,
  };
};

export default useWebSocket;
