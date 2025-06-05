import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { WebSocketMessage, RealTimeUpdate } from '../types/unified';
import { queryKeys } from './api/useUnifiedApi';

interface WebSocketConfig {
  url: string;
  protocols?: string | string[];
  options?: {
    maxReconnectAttempts?: number;
    reconnectInterval?: number;
    heartbeatInterval?: number;
  };
}

interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  lastMessage: WebSocketMessage | null;
  connectionAttempts: number;
}

export const useWebSocket = (config: WebSocketConfig) => {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastMessage: null,
    connectionAttempts: 0
  });

  const {
    maxReconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000
  } = config.options || {};

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      setState(prev => ({ ...prev, lastMessage: message }));

      // Handle different types of real-time updates
      switch (message.type) {
        case 'agent_status_update':
          // Invalidate agent queries to get fresh data
          queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
          break;
          
        case 'lead_update':
          // Invalidate lead queries
          queryClient.invalidateQueries({ queryKey: queryKeys.leads.all });
          queryClient.invalidateQueries({ queryKey: queryKeys.leads.byStage });
          break;
          
        case 'metrics_update':
          // Invalidate metrics queries
          queryClient.invalidateQueries({ queryKey: queryKeys.metrics.dashboard });
          queryClient.invalidateQueries({ queryKey: queryKeys.metrics.summary });
          break;
          
        case 'processing_progress':
          // Update processing progress for specific leads
          queryClient.invalidateQueries({ queryKey: queryKeys.leads.all });
          queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
          break;
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }, [queryClient]);

  const handleOpen = useCallback(() => {
    console.log('WebSocket connected');
    setState(prev => ({
      ...prev,
      isConnected: true,
      isConnecting: false,
      error: null,
      connectionAttempts: 0
    }));

    // Start heartbeat
    if (heartbeatInterval > 0) {
      heartbeatIntervalRef.current = setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'ping' }));
        }
      }, heartbeatInterval);
    }
  }, [heartbeatInterval]);

  const handleClose = useCallback((event: CloseEvent) => {
    console.log('WebSocket closed:', event.code, event.reason);
    
    setState(prev => ({
      ...prev,
      isConnected: false,
      isConnecting: false
    }));

    // Clear heartbeat
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    // Attempt to reconnect if not intentionally closed
    if (event.code !== 1000 && state.connectionAttempts < maxReconnectAttempts) {
      setState(prev => ({
        ...prev,
        connectionAttempts: prev.connectionAttempts + 1
      }));

      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, reconnectInterval * Math.pow(2, state.connectionAttempts)); // Exponential backoff
    }
  }, [state.connectionAttempts, maxReconnectAttempts, reconnectInterval]);

  const handleError = useCallback((event: Event) => {
    console.error('WebSocket error:', event);
    setState(prev => ({
      ...prev,
      error: 'WebSocket connection error',
      isConnecting: false
    }));
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    setState(prev => ({
      ...prev,
      isConnecting: true,
      error: null
    }));

    try {
      wsRef.current = new WebSocket(config.url, config.protocols);
      
      wsRef.current.addEventListener('open', handleOpen);
      wsRef.current.addEventListener('message', handleMessage);
      wsRef.current.addEventListener('close', handleClose);
      wsRef.current.addEventListener('error', handleError);
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setState(prev => ({
        ...prev,
        error: 'Failed to create WebSocket connection',
        isConnecting: false
      }));
    }
  }, [config.url, config.protocols, handleOpen, handleMessage, handleClose, handleError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.removeEventListener('open', handleOpen);
      wsRef.current.removeEventListener('message', handleMessage);
      wsRef.current.removeEventListener('close', handleClose);
      wsRef.current.removeEventListener('error', handleError);
      
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close(1000, 'Disconnecting');
      }
      
      wsRef.current = null;
    }

    setState({
      isConnected: false,
      isConnecting: false,
      error: null,
      lastMessage: null,
      connectionAttempts: 0
    });
  }, [handleOpen, handleMessage, handleClose, handleError]);

  const sendMessage = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    sendMessage
  };
};

// Specific hook for Nellia WebSocket connection
export const useNelliaWebSocket = () => {
  return useWebSocket({
    url: process.env.REACT_APP_WS_URL || 'ws://localhost:3001/ws',
    options: {
      maxReconnectAttempts: 10,
      reconnectInterval: 2000,
      heartbeatInterval: 30000
    }
  });
};

// Hook for connection status indicator
export const useConnectionStatus = () => {
  const { isConnected, isConnecting, error } = useNelliaWebSocket();

  const status = isConnected ? 'connected' : 
                 isConnecting ? 'connecting' : 
                 error ? 'error' : 'disconnected';

  const statusColor = {
    connected: 'text-green-400',
    connecting: 'text-yellow-400',
    error: 'text-red-400',
    disconnected: 'text-gray-400'
  }[status];

  const statusText = {
    connected: 'Connected',
    connecting: 'Connecting...',
    error: 'Connection Error',
    disconnected: 'Disconnected'
  }[status];

  return {
    status,
    statusColor,
    statusText,
    isConnected,
    isConnecting,
    error
  };
};
