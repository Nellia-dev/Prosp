import { QueryClient, QueryCache } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error: unknown) => {
      // TODO: Implement more sophisticated error handling, e.g., logging to a service
      console.error('Global query error:', error);
      // Example: Show a toast notification
      // import { toast } from 'sonner'; // Assuming sonner or similar is used
      // toast.error(`Query failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10, // 10 minutes (formerly cacheTime)
      retry: (failureCount, error: unknown) => {
        // Don't retry auth errors
        const axiosError = error as { response?: { status: number } };
        if (axiosError?.response?.status === 401) return false;
        if (axiosError?.response?.status === 403) return false;
        return failureCount < 3;
      },
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      // useErrorBoundary: false, // Removed, not a valid default option here
      // onError: (error: unknown) => { // Removed, QueryCache.onError handles global errors
      //   console.error('Query defaultOptions error:', error);
      // },
    },
    mutations: {
      retry: 1,
      // We could also add a global onError for mutations here if needed
      // onError: (error: unknown) => {
      //   console.error('Global mutation error:', error);
      // },
    },
  },
});
