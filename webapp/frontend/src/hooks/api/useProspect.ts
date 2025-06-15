import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
// import { toast } from 'sonner'; // Or your preferred toast library
import { prospectApi } from '@/services/api'; // Assuming prospectApi is defined in services/api.ts

// Types based on backend DTOs/responses - these should ideally be in a shared types file
// or generated from OpenAPI spec.
export interface StartProspectingRequest {
  searchQuery: string;
  maxSites?: number;
}

export interface ProspectJob {
  jobId: string | number;
  status: string; // e.g., 'started', 'active', 'completed', 'failed'
  // Add other relevant fields from backend's ProspectJobStatus if needed for display
  progress?: number | object;
  createdAt?: string; // ISO date string
  finishedAt?: string | null; // ISO date string
  error?: string | null;
  leadsCreated?: number;
}

export interface ProspectJobStatusDetails extends ProspectJob {
  data?: unknown; // Raw job data if needed
  result?: unknown; // Job result if completed
  processedAt?: string | null; // ISO date string
}

// Placeholder for toast notifications
const toast = {
  success: (message: string) => console.log(`Toast Success: ${message}`),
  error: (message: string) => console.error(`Toast Error: ${message}`),
};

export const useStartProspecting = () => {
  const queryClient = useQueryClient();

  return useMutation<
    { jobId: string | number; status: string }, // Expected success response type
    Error, // Expected error type
    StartProspectingRequest // Variables type
  >({
    mutationFn: (data: StartProspectingRequest) => prospectApi.start(data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['prospect', 'jobs'] });
      // Also invalidate status for the new job if its ID is immediately known and we want to fetch it
      // queryClient.invalidateQueries({ queryKey: ['prospect', 'job', data.jobId] });
      toast.success('Prospecting process started successfully!');
      console.log('Prospecting started, job ID:', data.jobId);
    },
    onError: (error: Error) => {
      toast.error(`Failed to start prospecting process: ${error.message}`);
      console.error('Failed to start prospecting:', error);
    },
  });
};

export const useProspectJobs = (refetchInterval = 5000) => {
  return useQuery<ProspectJob[], Error>({
    queryKey: ['prospect', 'jobs'],
    queryFn: prospectApi.getJobs,
    refetchInterval: refetchInterval,
    placeholderData: [], // Provide empty array as placeholder
    select: (data) => data || [], // Ensure it's always an array
  });
};

export const useProspectJobStatus = (jobId: string | number | null, enabled = true, refetchInterval = 2000) => {
  return useQuery<ProspectJobStatusDetails, Error>({
    queryKey: ['prospect', 'job', jobId],
    queryFn: () => {
      if (!jobId) return Promise.reject(new Error("Job ID is required"));
      return prospectApi.getJobStatus(jobId.toString()); // Ensure jobId is string for API call
    },
    enabled: !!jobId && enabled, // Only enable if jobId is present and enabled prop is true
    refetchInterval: refetchInterval,
    // placeholderData can be tricky for single item, might need a function or specific structure
    // placeholderData: () => ({ jobId, status: 'loading', progress: 0, ... }), // Example
  });
};
