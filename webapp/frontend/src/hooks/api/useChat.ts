import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '../../services/api';
import type { ChatMessageRequest, ChatMessageResponse } from '../../types/api';

// Query keys
export const chatKeys = {
  all: ['chat'] as const,
  messages: (agentId: string) => [...chatKeys.all, 'messages', agentId] as const,
};

// Hooks
export const useChatMessages = (agentId: string) => {
  return useQuery({
    queryKey: chatKeys.messages(agentId),
    queryFn: () => chatApi.getMessages(agentId),
    enabled: !!agentId,
  });
};

export const useSendMessage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ChatMessageRequest) => chatApi.sendMessage(data),
    onSuccess: (data, variables) => {
      // Add the new message to the cache
      queryClient.setQueryData(
        chatKeys.messages(variables.agentId),
        (oldData: ChatMessageResponse[] | undefined) => {
          if (!oldData) return [data];
          return [...oldData, data];
        }
      );
    },
  });
};
