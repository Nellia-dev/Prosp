import React, { useState } from 'react';
  import { useTranslation } from '../hooks/useTranslation';
  import { useProspectJobs, useStartProspectingJob, useBusinessContext, usePlanInfo } from '../hooks/api/useUnifiedApi';
  import type { ProspectJob } from '../types/api';
  import { useRealTimeEvent } from '../hooks/useRealTimeUpdates';
  import type { 
    LeadCreatedEvent, 
    JobCompletedEvent, 
    JobFailedEvent, 
    StatusUpdateEvent 
  } from '../types/events';
  import { Button } from "@/components/ui/button";
  import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
  import { Input } from "@/components/ui/input";
  import { Label } from "@/components/ui/label";
  import { Progress } from "@/components/ui/progress"; // For job progress
  import { Badge } from "@/components/ui/badge"; // For job status
  import { ScrollArea } from "@/components/ui/scroll-area"; // For job lists
  import { AlertCircle, CheckCircle, Hourglass, PlayCircle, ListChecks, Crown, Zap, TrendingUp } from 'lucide-react';
 
  // Placeholder for toast notifications
  const toast = {
    success: (message: string) => console.log(`Toast Success: ${message}`),
    error: (message: string) => console.error(`Toast Error: ${message}`),
  };
 
  // Align with our unified event types for better type safety
  interface EnrichmentEvent {
    event_type: string;
    timestamp: string;
    job_id: string;
    user_id: string;
    agent_name?: string;
    status_message?: string;
  }
 
  interface EnrichmentStatus {
    [jobId: string]: {
      events: EnrichmentEvent[];
      lastUpdate: string;
    };
  }
 
  // Child Component: ActiveJobsDisplay (Placeholder)
  const ActiveJobsDisplay = ({ jobs, enrichmentStatus, liveLeadsCount }: { jobs: ProspectJob[], enrichmentStatus: EnrichmentStatus, liveLeadsCount: number }) => {
    const { t } = useTranslation();
    if (!jobs || jobs.length === 0) return <p className="text-slate-400">{t('prospectDashboard.noActiveJobs')}</p>;

    return (
      <div className="space-y-4">
        {jobs.map(job => {
          const enrichment = enrichmentStatus[job.jobId];
          const lastEvent = enrichment?.events?.[enrichment.events.length - 1];
          const agentName = lastEvent?.agent_name;
          const progress = enrichment ? (enrichment.events.length / 15) * 100 : job.progress;

          return (
            <Card key={job.jobId} className="bg-slate-800 border-slate-700">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle className="text-slate-200 text-lg">{t('prospectDashboard.jobId')}: {job.jobId}</CardTitle>
                  <Badge variant={job.status === 'active' ? 'default' : 'secondary'} className={
                    job.status === 'active' ? 'bg-blue-500 text-white' :
                    job.status === 'waiting' ? 'bg-yellow-500 text-black' : 'bg-slate-600 text-slate-300'
                  }>
                    {job.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex justify-between items-center mb-2">
                    <p className="text-sm text-slate-300">Status</p>
                    <p className="text-sm font-medium text-slate-100">Harvesting & Enriching...</p>
                </div>
                <div className="flex justify-between items-center">
                    <p className="text-sm text-slate-300">Leads Found</p>
                    <p className="text-sm font-medium text-green-400">{liveLeadsCount}</p>
                </div>
                {typeof progress === 'number' && (
                  <div className="mt-4">
                    <Progress value={progress} className="w-full [&>div]:bg-green-500" />
                    <p className="text-sm text-slate-400 mt-1">{progress.toFixed(0)}% {t('common.complete')}</p>
                    {agentName && <p className="text-xs text-slate-500 mt-1">Current Agent: {agentName}</p>}
                  </div>
                )}
                <p className="text-xs text-slate-500 mt-4">{t('common.createdAt')}: {new Date(job.createdAt || Date.now()).toLocaleString()}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    );
  };
 
  // Child Component: ReadyToProspectDisplay (Placeholder)
  const ReadyToProspectDisplay = () => {
    const { t } = useTranslation();
    return (
      <div className="text-center py-8">
        <PlayCircle className="w-16 h-16 mx-auto mb-4 text-green-500" />
        <h3 className="text-xl font-semibold text-slate-200 mb-2">{t('prospectDashboard.readyToProspectTitle')}</h3>
        <p className="text-slate-400">{t('prospectDashboard.readyToProspectDescription')}</p>
      </div>
    );
  };
 
  // Child Component: RecentJobsList (Placeholder)
  const RecentJobsList = ({ jobs }: { jobs: ProspectJob[] }) => {
    const { t } = useTranslation();
    if (!jobs || jobs.length === 0) return <p className="text-slate-400">{t('prospectDashboard.noRecentJobs')}</p>;
 
    const getStatusIcon = (status: string) => {
      if (status === 'completed') return <CheckCircle className="w-4 h-4 text-green-500 mr-2" />;
      if (status === 'failed') return <AlertCircle className="w-4 h-4 text-red-500 mr-2" />;
      if (['active', 'waiting'].includes(status)) return <Hourglass className="w-4 h-4 text-blue-500 mr-2 animate-spin" />;
      return <ListChecks className="w-4 h-4 text-slate-500 mr-2" />;
    };
 
    return (
      <ScrollArea className="h-[300px] pr-4">
        <ul className="space-y-3">
          {jobs.map(job => (
            <li key={job.jobId} className="p-3 bg-slate-800 rounded-md border border-slate-700 hover:bg-slate-700/50 transition-colors">
              <div className="flex justify-between items-center">
                <span className="text-slate-300 font-medium">{t('prospectDashboard.jobId')}: {job.jobId}</span>
                <Badge variant={job.status === 'completed' ? 'default' : job.status === 'failed' ? 'destructive' : 'secondary'}
                  className={
                    job.status === 'completed' ? 'bg-green-600' : 
                    job.status === 'failed' ? 'bg-red-600' : 'bg-slate-600'
                  }
                >
                  {getStatusIcon(job.status)}
                  {t(`prospectDashboard.jobStatus.${job.status}`)} 
                </Badge>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {t('common.createdAt')}: {new Date(job.createdAt || Date.now()).toLocaleDateString()}
                {job.finishedAt && ` - ${t('common.finishedAt')}: ${new Date(job.finishedAt).toLocaleDateString()}`}
              </p>
              {job.error && <p className="text-xs text-red-400 mt-1">{t('common.error')}: {job.error}</p>}
              {/* For translations with counts, the i18n library usually handles pluralization.
                  Assuming your setup supports passing count in options or has specific keys for plurals.
                  If using i18next, it would be t('key', { count: value })
                  For the custom hook, it might need adjustment or specific keys like 'prospectDashboard.leadsCreated_one', 'prospectDashboard.leadsCreated_other'
                  For simplicity, I'll use a simple t() call here. You might need to adjust your i18n setup.
              */}
              {job.leadsCreated !== undefined && <p className="text-xs text-green-400 mt-1">{t('prospectDashboard.leadsCreated')}: {job.leadsCreated}</p>}
            </li>
          ))}
        </ul>
      </ScrollArea>
    );
  };
 
  // Child Component: PlanStatusCard
  const PlanStatusCard = () => {
    const { t } = useTranslation();
    const { 
      plan, 
      quota, 
      quotaUsagePercentage, 
      isQuotaExhausted, 
      quotaDisplay, 
      nextResetFormatted,
      isLoading,
      error 
    } = usePlanInfo();
 
    if (isLoading) {
      return (
        <Card className="bg-slate-800/80 border-slate-700 shadow-xl">
          <CardContent className="p-6">
            <div className="animate-pulse">
              <div className="h-4 bg-slate-600 rounded w-1/3 mb-2"></div>
              <div className="h-8 bg-slate-600 rounded w-1/2"></div>
            </div>
          </CardContent>
        </Card>
      );
    }
 
    if (error || !plan || !quota) {
      return (
        <Card className="bg-slate-800/80 border-slate-700 shadow-xl">
          <CardContent className="p-6">
            <div className="flex items-center text-amber-400">
              <AlertCircle className="w-4 h-4 mr-2" />
              <span className="text-sm">{t('planStatus.loadError')}</span>
            </div>
          </CardContent>
        </Card>
      );
    }
 
    const getPlanIcon = (planId: string) => {
      switch (planId) {
        case 'free': return <Zap className="w-5 h-5 text-slate-400" />;
        case 'starter': return <TrendingUp className="w-5 h-5 text-blue-400" />;
        case 'pro': return <Crown className="w-5 h-5 text-purple-400" />;
        case 'enterprise': return <Crown className="w-5 h-5 text-gold-400" />;
        default: return <Zap className="w-5 h-5 text-slate-400" />;
      }
    };
 
    const getQuotaColor = () => {
      if (quotaUsagePercentage >= 90) return 'text-red-400';
      if (quotaUsagePercentage >= 70) return 'text-amber-400';
      return 'text-green-400';
    };
 
    const getProgressColor = () => {
      if (quotaUsagePercentage >= 90) return '[&>div]:bg-red-500';
      if (quotaUsagePercentage >= 70) return '[&>div]:bg-amber-500';
      return '[&>div]:bg-green-500';
    };
 
    return (
      <Card className="bg-slate-800/80 border-slate-700 shadow-xl">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center text-slate-100 text-lg">
            {getPlanIcon(plan.id)}
            <span className="ml-2">{plan.name} {t('planStatus.plan')}</span>
            {isQuotaExhausted && (
              <Badge variant="destructive" className="ml-auto">
                {t('planStatus.quotaExhausted')}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-slate-300">{t('planStatus.quotaUsage')}</span>
              <span className={`text-sm font-medium ${getQuotaColor()}`}>
                {quotaDisplay}
              </span>
            </div>
            <Progress 
              value={quotaUsagePercentage} 
              className={`w-full ${getProgressColor()}`}
            />
            <div className="flex justify-between items-center mt-1">
              <span className="text-xs text-slate-500">
                {quota.remaining} {t('planStatus.remaining')}
              </span>
              {nextResetFormatted && (
                <span className="text-xs text-slate-500">
                  {t('planStatus.resetDate')}: {nextResetFormatted}
                </span>
              )}
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-400">{t('planStatus.period')}</span>
              <p className="text-slate-200 font-medium capitalize">{plan.period}</p>
            </div>
            <div>
              <span className="text-slate-400">{t('planStatus.totalQuota')}</span>
              <p className="text-slate-200 font-medium">
                {plan.quota === Infinity ? '∞' : plan.quota}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };
 
 
 
  export const ProspectDashboard = () => {
    const { t } = useTranslation();
    const [enrichmentStatus, setEnrichmentStatus] = useState<EnrichmentStatus>({});
    const { data: jobsData = [], isLoading: jobsLoading, error: jobsError, refetch: refetchJobs } = useProspectJobs();
    const { mutate: startProspectingJob, isPending: startProspectingLoading } = useStartProspectingJob();
    const { data: businessContext, isLoading: businessContextLoading } = useBusinessContext();
    const { canStartProspecting, hasActiveJob, isQuotaExhausted, isLoading: planLoading } = usePlanInfo();
    const [liveLeadsCount, setLiveLeadsCount] = useState(0);

    // Listen for new leads being generated in real-time
    useRealTimeEvent('lead-created', () => {
      setLiveLeadsCount(prev => prev + 1);
      // Optionally, you can invalidate the leads query to refetch the list
      // queryClient.invalidateQueries({ queryKey: ['leads'] });
    });

    // Listen for the overall job to end to reset local state
    useRealTimeEvent('job-completed', () => {
        setLiveLeadsCount(0);
        refetchJobs();
    });
    useRealTimeEvent('job-failed', () => {
        setLiveLeadsCount(0);
        refetchJobs();
    });

    useRealTimeEvent<StatusUpdateEvent>('enrichment-update', (data) => {
      if ('job_id' in data) {
        const job_id = data.job_id as string;
        setEnrichmentStatus(prev => ({
          ...prev,
          [job_id]: {
            ...prev[job_id],
            events: [...(prev[job_id]?.events || []), data],
            lastUpdate: new Date().toISOString(),
          },
        }));
      }
    });

    // Ensure jobsData is always an array, even if API returns null/undefined initially
    const jobs: ProspectJob[] = Array.isArray(jobsData) ? jobsData : [];

    const activeJobs = jobs.filter(job => job && ['waiting', 'active'].includes(job.status));
    const recentJobs = jobs.slice(0, 5); // Assuming jobs are sorted by date descending from API or hook
 
    const handleStartProspecting = () => {
      if (businessContext) {
        startProspectingJob(businessContext, {
          onSuccess: () => {
            toast.success(t('prospectDashboard.jobStartedSuccess'));
          },
          onError: (error) => {
            toast.error(`${t('prospectDashboard.jobStartedError')}: ${error.message}`);
          },
        });
      } else {
        toast.error(t('prospectDashboard.businessContextMissingError'));
      }
    };
 
    // Determine if prospecting should be disabled
    const isProspectingDisabled = () => {
      if (planLoading || businessContextLoading) return true;
      if (activeJobs.length > 0 || hasActiveJob) return true;
      if (!canStartProspecting || isQuotaExhausted) return true;
      if (startProspectingLoading) return true;
      if (!businessContext) return true;
      return false;
    };
 
    // Get the appropriate button text and tooltip
    const getButtonText = () => {
      if (activeJobs.length > 0 || hasActiveJob) {
        return t('prospectDashboard.processRunningButton');
      }
      if (isQuotaExhausted) {
        return t('prospectDashboard.quotaExhaustedButton');
      }
      if (!canStartProspecting) {
        return t('prospectDashboard.cannotStartButton');
      }
      return t('prospectDashboard.startProspectingButton');
    };
    
    if (jobsLoading || businessContextLoading) {
      return <p className="text-slate-300 p-4">{t('common.loading')}...</p>;
    }
 
    if (jobsError) {
      return <p className="text-red-400 p-4">{t('common.errorLoadingData')}: {jobsError.message}</p>;
    }
 
    return (
      <div className="space-y-6 p-4">
        {/* Plan Status Card */}
        <PlanStatusCard />
 
        {/* Main Prospecting Card */}
        <Card className="bg-slate-800/80 border-slate-700 shadow-xl">
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-slate-100">
              {t('prospectDashboard.title')}
              <Button 
                onClick={handleStartProspecting}
                disabled={isProspectingDisabled()}
                className={`${
                  isQuotaExhausted 
                    ? 'bg-red-600 hover:bg-red-700' 
                    : 'bg-green-600 hover:bg-green-700'
                }`}
              >
                {getButtonText()}
              </Button>
            </CardTitle>
            <CardDescription className="text-slate-400">
              {t('prospectDashboard.description')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {activeJobs.length > 0 ? (
              <ActiveJobsDisplay jobs={activeJobs} enrichmentStatus={enrichmentStatus} liveLeadsCount={liveLeadsCount} />
            ) : (
              <ReadyToProspectDisplay />
            )}
          </CardContent>
        </Card>
 
        {/* Recent Jobs Card */}
        {recentJobs.length > 0 && (
          <Card className="bg-slate-800/80 border-slate-700 shadow-xl">
            <CardHeader>
              <CardTitle className="text-slate-100">{t('prospectDashboard.recentJobsTitle')}</CardTitle>
            </CardHeader>
            <CardContent>
              <RecentJobsList jobs={recentJobs} />
            </CardContent>
          </Card>
        )}
 
      </div>
    );
  };
