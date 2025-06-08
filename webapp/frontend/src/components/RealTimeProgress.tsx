import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { RocketIcon } from 'lucide-react';

interface JobProgressEvent {
  jobId: string;
  userId: string;
  status: string;
  progress: number;
  currentStep?: string;
  searchQuery?: string;
  timestamp: string;
}

interface EnrichmentEvent {
  event_type: string;
  job_id: string;
  [key: string]: unknown;
}

export function RealTimeProgress() {
  const { data: jobStatus } = useQuery<JobProgressEvent>({
    queryKey: ['prospect-job-status'],
    enabled: false, // This query is populated by the WebSocket
  });

  const { data: enrichmentStatus } = useQuery<{ events: EnrichmentEvent[] }>({
    queryKey: ['enrichment-status', jobStatus?.jobId],
    enabled: !!jobStatus,
  });

  if (!jobStatus) {
    return null; // Don't render anything if there's no active job
  }

  const lastEnrichmentEvent = enrichmentStatus?.events?.[enrichmentStatus.events.length - 1];

  return (
    <div className="fixed bottom-4 right-4 w-96 z-50">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <RocketIcon className="mr-2" />
            Nellia is Working...
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Alert>
              <AlertTitle>Harvesting Leads</AlertTitle>
              <AlertDescription>{jobStatus.currentStep || 'Initializing...'}</AlertDescription>
              <Progress value={jobStatus.progress} className="mt-2" />
            </Alert>

            {lastEnrichmentEvent && (
              <Alert>
                <AlertTitle>Enriching Lead</AlertTitle>
                <AlertDescription>
                  {lastEnrichmentEvent.event_type}: {(lastEnrichmentEvent.agent_name as string) || ''}
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}