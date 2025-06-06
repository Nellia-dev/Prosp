import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { io, Socket } from 'socket.io-client';
import { API_CONFIG } from '../config/api';
import { queryKeys } from './api/useUnifiedApi';

interface SocketMessage {
  type: string;
  data?: unknown;
  timestamp?: string;
}

interface SocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  lastMessage: SocketMessage | null;
  connectionAttempts: number;
}

interface SocketConfig {
  url?: string;
  options?: {
    maxReconnectAttempts?: number;
    reconnectInterval?: number;
    heartbeatInterval?: number;
    autoConnect?: boolean;
  };
}

export const useSocketIO = (config: SocketConfig = {}) => {
  const queryClient = useQueryClient();
  const socketRef = useRef<Socket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const [state, setState] = useState<SocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastMessage: null,
    connectionAttempts: 0
  });

  const {
    maxReconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000,
    autoConnect = true
  } = config.options || {};

  const socketUrl = config.url || API_CONFIG.WS_URL;

  const handleConnect = useCallback(() => {
    console.log('Socket.IO connected');
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
        if (socketRef.current?.connected) {
          socketRef.current.emit('heartbeat');
        }
      }, heartbeatInterval);
    }
  }, [heartbeatInterval]);

  const handleDisconnect = useCallback((reason: string) => {
    console.log('Socket.IO disconnected:', reason);
    
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

    // Only attempt reconnection for certain disconnect reasons
    if (reason === 'io server disconnect' || reason === 'ping timeout') {
      setState(prev => ({
        ...prev,
        error: `Connection lost: ${reason}`
      }));
    }
  }, []);

  const handleConnectError = useCallback((error: Error) => {
    console.error('Socket.IO connection error:', error);
    setState(prev => ({
      ...prev,
      error: `Connection failed: ${error.message}`,
      isConnecting: false,
      connectionAttempts: prev.connectionAttempts + 1
    }));
  }, []);

  const handleMessage = useCallback((eventName: string, data: unknown) => {
    const message: SocketMessage = {
      type: eventName,
      data,
      timestamp: new Date().toISOString()
    };

    setState(prev => ({ ...prev, lastMessage: message }));

    // Handle different types of real-time updates
    switch (eventName) {
      case 'agent-status-update':
      case 'agent-metrics-update':
        queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
        break;
        
      case 'lead-created':
      case 'lead-updated':
      case 'lead-stage-changed':
        queryClient.invalidateQueries({ queryKey: queryKeys.leads.all });
        queryClient.invalidateQueries({ queryKey: queryKeys.leads.byStage });
        break;
        
      case 'metrics-update':
      case 'dashboard-update':
        queryClient.invalidateQueries({ queryKey: queryKeys.metrics.dashboard });
        queryClient.invalidateQueries({ queryKey: queryKeys.metrics.summary });
        break;
        
      case 'processing-progress':
        queryClient.invalidateQueries({ queryKey: queryKeys.leads.all });
        queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
        break;

      case 'heartbeat-response':
        // Handle heartbeat response
        console.debug('Heartbeat response received');
        break;
    }
  }, [queryClient]);

  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return;
    }

    setState(prev => ({
      ...prev,
      isConnecting: true,
      error: null
    }));

    try {
      socketRef.current = io(socketUrl, {
        transports: ['websocket', 'polling'],
        autoConnect: false,
        reconnection: true,
        reconnectionAttempts: maxReconnectAttempts,
        reconnectionDelay: reconnectInterval,
        timeout: 20000,
      });

      // Set up event listeners
      socketRef.current.on('connect', handleConnect);
      socketRef.current.on('disconnect', handleDisconnect);
      socketRef.current.on('connect_error', handleConnectError);

      // Set up message listeners for real-time updates
      const eventTypes = [
        'agent-status-update',
        'agent-metrics-update',
        'lead-created',
        'lead-updated',
        'lead-stage-changed',
        'metrics-update',
        'dashboard-update',
        'processing-progress',
        'heartbeat-response',
        'subscription-confirmed',
        'subscription-error',
        'unsubscription-confirmed',
        'connection-stats',
        'quota-updated',
        'job-progress',
        'job-completed',
        'job-failed',
        'enrichment-update',
        'lead-update'
      ];

      eventTypes.forEach(eventType => {
        socketRef.current?.on(eventType, (data) => handleMessage(eventType, data));
      });

      // Connect
      socketRef.current.connect();
      
    } catch (error) {
      console.error('Failed to create Socket.IO connection:', error);
      setState(prev => ({
        ...prev,
        error: 'Failed to create Socket.IO connection',
        isConnecting: false
      }));
    }
  }, [socketUrl, maxReconnectAttempts, reconnectInterval, handleConnect, handleDisconnect, handleConnectError, handleMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (socketRef.current) {
      socketRef.current.removeAllListeners();
      socketRef.current.disconnect();
      socketRef.current = null;
    }

    setState({
      isConnected: false,
      isConnecting: false,
      error: null,
      lastMessage: null,
      connectionAttempts: 0
    });
  }, []);

  const emit = useCallback((event: string, data?: unknown) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
      return true;
    }
    return false;
  }, []);

  const subscribe = useCallback((entities: string[]) => {
    return emit('subscribe', { entities });
  }, [emit]);

  const unsubscribe = useCallback((entities: string[]) => {
    return emit('unsubscribe', { entities });
  }, [emit]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, []); // Remove dependencies to prevent infinite re-renders

  return {
    ...state,
    connect,
    disconnect,
    emit,
    subscribe,
    unsubscribe
  };
};

// Specific hook for Nellia Socket.IO connection
export const useNelliaSocket = () => {
  return useSocketIO({
    options: {
      maxReconnectAttempts: 10,
      reconnectInterval: 2000,
      heartbeatInterval: 30000,
      autoConnect: true
    }
  });
};

// Hook for connection status indicator
export const useConnectionStatus = () => {
  const { isConnected, isConnecting, error } = useNelliaSocket();

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
