import React, { createContext, useContext, useEffect, ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { LeadResponse } from '../types/api';
import { LeadGeneratedEvent, StatusUpdateEvent } from '../types/events';
import { queryKeys } from '../hooks/api/useUnifiedApi';

const WebSocketContext = createContext<null>(null);

export const useWebSocket = () => useContext(WebSocketContext);

interface UnifiedApiProviderProps {
  children: ReactNode;
}

const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws/v1/updates';

export const UnifiedApiProvider = ({ children }: UnifiedApiProviderProps) => {
  const queryClient = useQueryClient();

  useEffect(() => {
    console.log('Connecting to WebSocket at:', WEBSOCKET_URL);
    const ws = new WebSocket(WEBSOCKET_URL);

    ws.onopen = () => {
      console.log('WebSocket connection established.');
    };

    ws.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data);
        console.log('Received event:', eventData);

        switch (eventData.event_type) {
          case 'lead_generated':
            const leadEvent = eventData as LeadGeneratedEvent;
            const newLead = leadEvent.lead_data;
            queryClient.setQueryData<LeadResponse[]>(queryKeys.leads.all, (oldData = []) => [
              newLead,
              ...oldData,
            ]);
            break;

          case 'status_update':
            const statusEvent = eventData as StatusUpdateEvent;
            queryClient.setQueryData<LeadResponse[]>(queryKeys.leads.all, (oldData = []) =>
              oldData.map(lead =>
                lead.id === statusEvent.lead_id
                  ? { ...lead, status: statusEvent.status, status_message: statusEvent.message }
                  : lead
              )
            );
            break;

          default:
            break;
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed.');
      // Optional: implement reconnection logic here
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    // Cleanup on component unmount
    return () => {
      ws.close();
    };
  }, [queryClient]);

  return (
    <WebSocketContext.Provider value={null}>
      {children}
    </WebSocketContext.Provider>
  );
};
