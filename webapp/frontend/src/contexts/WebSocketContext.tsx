import React, { createContext, useContext, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocket, WebSocketState, NotificationData, MetricsUpdateData } from '../hooks/useWebSocket';
import { useAuth } from './AuthContext';
import { AgentStatus, LeadData } from '../types/nellia';
import { useToast } from '../hooks/use-toast';

interface WebSocketContextType extends WebSocketState {
  connect: () => void;
  disconnect: () => void;
  emit: (event: string, data?: unknown) => boolean;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocketContext = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: React.ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Handle agent status updates
  const handleAgentStatusUpdate = useCallback((agentId: string, status: Partial<AgentStatus>) => {
    // Update specific agent in cache
    queryClient.setQueryData(['agents', agentId], (oldData: AgentStatus | undefined) => {
      if (!oldData) return oldData;
      return { ...oldData, ...status };
    });

    // Invalidate agents list to trigger refetch
    queryClient.invalidateQueries({ queryKey: ['agents'], exact: false });

    // Show toast notification for significant status changes
    if (status.status) {
      toast({
        title: 'Agent Status Update',
        description: `Agent ${status.name || agentId} is now ${status.status}`,
        variant: status.status === 'error' ? 'destructive' : 'default',
      });
    }
  }, [queryClient, toast]);

  // Handle lead updates
  const handleLeadUpdate = useCallback((leadId: string, data: Partial<LeadData>) => {
    // Update specific lead in cache
    queryClient.setQueryData(['leads', leadId], (oldData: LeadData | undefined) => {
      if (!oldData) return oldData;
      return { ...oldData, ...data };
    });

    // Invalidate related queries
    queryClient.invalidateQueries({ queryKey: ['leads'], exact: false });
    queryClient.invalidateQueries({ queryKey: ['leads', 'by-stage'] });

    // Show notification for stage changes
    if (data.processing_stage) {
      toast({
        title: 'Lead Updated',
        description: `Lead ${data.company_name || leadId} moved to ${data.processing_stage}`,
      });
    }
  }, [queryClient, toast]);

  // Handle metrics updates
  const handleMetricsUpdate = useCallback((metrics: MetricsUpdateData) => {
    // Update metrics cache
    if (metrics.dashboardMetrics) {
      queryClient.setQueryData(['metrics', 'dashboard'], metrics.dashboardMetrics);
    }
    
    if (metrics.agentMetrics) {
      queryClient.setQueryData(['metrics', 'agents'], metrics.agentMetrics);
    }
    
    if (metrics.performanceData) {
      queryClient.setQueryData(['metrics', 'performance'], metrics.performanceData);
    }

    // Invalidate metrics queries to ensure fresh data
    queryClient.invalidateQueries({ queryKey: ['metrics'], exact: false });
  }, [queryClient]);

  // Handle notifications
  const handleNotification = useCallback((notification: NotificationData) => {
    toast({
      title: notification.title,
      description: notification.message,
      variant: notification.type === 'error' ? 'destructive' : 'default',
    });
  }, [toast]);

  // Handle connection events
  const handleConnect = useCallback(() => {
    toast({
      title: 'Connected',
      description: 'Real-time updates are now active',
      variant: 'default',
    });
  }, [toast]);

  const handleDisconnect = useCallback((reason: string) => {
    toast({
      title: 'Disconnected',
      description: `Real-time updates paused: ${reason}`,
      variant: 'destructive',
    });
  }, [toast]);

  const handleError = useCallback((error: Error) => {
    console.error('WebSocket error:', error);
    toast({
      title: 'Connection Error',
      description: 'Failed to establish real-time connection',
      variant: 'destructive',
    });
  }, [toast]);

  // Initialize WebSocket with event handlers
  const webSocketState = useWebSocket(
    {
      autoConnect: true,
      reconnectEnabled: true,
      maxReconnectAttempts: 5,
      reconnectDelay: 1000,
    },
    {
      onAgentStatusUpdate: handleAgentStatusUpdate,
      onLeadUpdate: handleLeadUpdate,
      onMetricsUpdate: handleMetricsUpdate,
      onNotification: handleNotification,
      onConnect: handleConnect,
      onDisconnect: handleDisconnect,
      onError: handleError,
    }
  );

  const contextValue: WebSocketContextType = {
    ...webSocketState,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

export default WebSocketProvider;
