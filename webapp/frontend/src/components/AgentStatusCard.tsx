import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { 
  Activity, 
  Clock, 
  TrendingUp, 
  Users, 
  Play, 
  Square,
  Info,
  Zap,
  Brain,
  Settings,
  Target
} from "lucide-react";
import { ExtendedAgentResponse } from "../types/unified";
import { useTranslation } from "../hooks/useTranslation";
import { useStartAgent, useStopAgent } from "../hooks/api/useUnifiedApi";
import { useState } from "react";

interface AgentStatusCardProps {
  agent: ExtendedAgentResponse;
  showControls?: boolean;
  onAgentClick?: (agent: ExtendedAgentResponse) => void;
}

export const AgentStatusCard = ({ 
  agent, 
  showControls = true,
  onAgentClick 
}: AgentStatusCardProps) => {
  const { t } = useTranslation();
  const [isActioning, setIsActioning] = useState(false);
  
  const startAgentMutation = useStartAgent();
  const stopAgentMutation = useStopAgent();

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

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'initial_processing': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'orchestrator': return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'specialized': return 'bg-green-100 text-green-800 border-green-200';
      case 'alternative': return 'bg-orange-100 text-orange-800 border-orange-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'initial_processing': return <Target className="w-3 h-3" />;
      case 'orchestrator': return <Brain className="w-3 h-3" />;
      case 'specialized': return <Zap className="w-3 h-3" />;
      case 'alternative': return <Settings className="w-3 h-3" />;
      default: return <Activity className="w-3 h-3" />;
    }
  };

  const handleStartAgent = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isActioning) return;
    
    setIsActioning(true);
    try {
      await startAgentMutation.mutateAsync({ agentId: agent.id });
    } catch (error) {
      console.error('Failed to start agent:', error);
    } finally {
      setIsActioning(false);
    }
  };

  const handleStopAgent = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isActioning) return;
    
    setIsActioning(true);
    try {
      await stopAgentMutation.mutateAsync({ agentId: agent.id });
    } catch (error) {
      console.error('Failed to stop agent:', error);
    } finally {
      setIsActioning(false);
    }
  };

  const handleCardClick = () => {
    if (onAgentClick) {
      onAgentClick(agent);
    }
  };

  return (
    <Card 
      className={`relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700 hover:border-green-500/50 transition-all duration-300 ${
        onAgentClick ? 'cursor-pointer' : ''
      }`}
      onClick={handleCardClick}
    >
      <div className={`absolute top-0 left-0 w-1 h-full ${getStatusColor(agent.status)}`} />
      
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-white text-sm font-medium mb-1">
              {agent.displayName}
            </CardTitle>
            {agent.category && (
              <div className="flex items-center mb-2">
                <Badge 
                  variant="outline" 
                  className={`text-xs border ${getCategoryColor(agent.category)}`}
                >
                  {getCategoryIcon(agent.category)}
                  <span className="ml-1 capitalize">
                    {agent.category.replace('_', ' ')}
                  </span>
                </Badge>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={getStatusBadgeVariant(agent.status)} className="text-xs">
              {t(agent.status)}
            </Badge>
            {showControls && (
              <div className="flex items-center gap-1">
                {agent.status === 'inactive' ? (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 w-6 p-0"
                    onClick={handleStartAgent}
                    disabled={isActioning || startAgentMutation.isPending}
                  >
                    <Play className="w-3 h-3" />
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 w-6 p-0"
                    onClick={handleStopAgent}
                    disabled={isActioning || stopAgentMutation.isPending}
                  >
                    <Square className="w-3 h-3" />
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
        
        {agent.description && (
          <p className="text-slate-400 text-xs leading-relaxed">
            {agent.description}
          </p>
        )}
        
        {agent.current_task && (
          <p className="text-blue-400 text-xs truncate bg-blue-950/30 px-2 py-1 rounded">
            <Activity className="w-3 h-3 inline mr-1" />
            {agent.current_task}
          </p>
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
              {agent.metrics.success_rate.toFixed(1)}%
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
          <div className="flex justify-between text-xs text-slate-500">
            <span>Prompt: {agent.metrics.llm_usage.prompt_tokens.toLocaleString()}</span>
            <span>Completion: {agent.metrics.llm_usage.completion_tokens.toLocaleString()}</span>
          </div>
        </div>

        {agent.last_updated && (
          <div className="text-xs text-slate-500 border-t border-slate-700 pt-2">
            Last updated: {new Date(agent.last_updated).toLocaleTimeString()}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
