
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Activity, Clock, TrendingUp, Users } from "lucide-react";
import { AgentStatus } from "../types/nellia";
import { useTranslation } from "../hooks/useTranslation";

interface AgentStatusCardProps {
  agent: AgentStatus;
}

export const AgentStatusCard = ({ agent }: AgentStatusCardProps) => {
  const { t } = useTranslation();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'processing': return 'bg-blue-500';
      case 'error': return 'bg-red-500';
      case 'completed': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'active': return 'default';
      case 'processing': return 'secondary';
      case 'error': return 'destructive';
      default: return 'outline';
    }
  };

  return (
    <Card className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700 hover:border-green-500/50 transition-all duration-300">
      <div className={`absolute top-0 left-0 w-1 h-full ${getStatusColor(agent.status)}`} />
      
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-white text-sm font-medium">
            {t(agent.name.toLowerCase().replace(/\s+/g, '_'))}
          </CardTitle>
          <Badge variant={getStatusBadgeVariant(agent.status)} className="text-xs">
            {t(agent.status)}
          </Badge>
        </div>
        {agent.current_task && (
          <p className="text-slate-400 text-xs truncate">{agent.current_task}</p>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <div className="flex items-center text-slate-400 text-xs">
              <Clock className="w-3 h-3 mr-1" />
              {t('processing_time')}
            </div>
            <p className="text-white text-sm font-medium">
              {agent.metrics.processing_time_seconds.toFixed(1)}s
            </p>
          </div>

          <div className="space-y-1">
            <div className="flex items-center text-slate-400 text-xs">
              <TrendingUp className="w-3 h-3 mr-1" />
              {t('success_rate')}
            </div>
            <p className="text-white text-sm font-medium">
              {(agent.metrics.success_rate * 100).toFixed(1)}%
            </p>
          </div>

          <div className="space-y-1">
            <div className="flex items-center text-slate-400 text-xs">
              <Users className="w-3 h-3 mr-1" />
              {t('queue_depth')}
            </div>
            <p className="text-white text-sm font-medium">
              {agent.metrics.queue_depth}
            </p>
          </div>

          <div className="space-y-1">
            <div className="flex items-center text-slate-400 text-xs">
              <Activity className="w-3 h-3 mr-1" />
              {t('throughput')}
            </div>
            <p className="text-white text-sm font-medium">
              {agent.metrics.throughput_per_hour}/h
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">{t('token_usage')}</span>
            <span className="text-white">{agent.metrics.llm_usage.total_tokens.toLocaleString()}</span>
          </div>
          <Progress 
            value={Math.min((agent.metrics.llm_usage.total_tokens / 100000) * 100, 100)} 
            className="h-1"
          />
        </div>
      </CardContent>
    </Card>
  );
};
