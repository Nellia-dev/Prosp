
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { TrendingUp, Users, Clock, Target, Loader2 } from "lucide-react";
import { useTranslation } from "../hooks/useTranslation";
import { usePerformanceMetrics, useAgentPerformanceMetrics, useMetricsSummary } from "../hooks/api/useMetrics";

export const MetricsVisualization = () => {
  const { t } = useTranslation();
  
  // API calls
  const { data: performanceData, isLoading: performanceLoading } = usePerformanceMetrics('24h');
  const { data: agentPerformanceData, isLoading: agentLoading } = useAgentPerformanceMetrics();
  const { data: summaryData, isLoading: summaryLoading } = useMetricsSummary();

  // Loading state
  if (performanceLoading || agentLoading || summaryLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
          <CardContent className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-green-500" />
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
          <CardContent className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-green-500" />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Transform data for charts
  const chartPerformanceData = performanceData ? [
    ...performanceData.throughputData.map(item => ({
      time: new Date(item.timestamp).toLocaleTimeString('pt-BR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      }),
      throughput: item.value,
      processing_time: performanceData.processingTimeData.find(
        p => p.timestamp === item.timestamp
      )?.value || 0
    }))
  ] : [];

  const chartAgentData = agentPerformanceData?.map(agent => ({
    agent: agent.agentName,
    success: agent.successCount,
    errors: agent.errorCount
  })) || [];

  // Get summary metrics with fallbacks
  const averageROI = summaryData?.overview?.averageROI || 0;
  const processedLeads = summaryData?.overview?.processedLeads || 0;
  const averageProcessingTime = summaryData?.overview?.averageProcessingTime || 0;
  const successRate = summaryData?.overview?.successRate || 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white text-lg flex items-center">
            <TrendingUp className="w-5 h-5 mr-2 text-green-500" />
            Performance Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-400">
                {averageROI > 0 ? `${averageROI.toFixed(0)}%` : 'N/A'}
              </div>
              <div className="text-xs text-slate-400">ROI Médio</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400">
                {processedLeads.toLocaleString()}
              </div>
              <div className="text-xs text-slate-400">Leads Processados</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-400">
                {averageProcessingTime > 0 ? `${averageProcessingTime.toFixed(1)}s` : 'N/A'}
              </div>
              <div className="text-xs text-slate-400">Tempo Médio</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-400">
                {successRate > 0 ? `${(successRate * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <div className="text-xs text-slate-400">Taxa de Sucesso</div>
            </div>
          </div>
          
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartPerformanceData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Line type="monotone" dataKey="throughput" stroke="#10B981" strokeWidth={2} />
              <Line type="monotone" dataKey="processing_time" stroke="#3B82F6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white text-lg flex items-center">
            <Target className="w-5 h-5 mr-2 text-blue-500" />
            Agent Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartAgentData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="agent" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="success" fill="#10B981" />
              <Bar dataKey="errors" fill="#EF4444" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
};
