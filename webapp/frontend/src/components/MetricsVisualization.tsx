import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  BarChart, 
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { 
  TrendingUp, 
  Users, 
  Clock, 
  Target, 
  Loader2, 
  Activity,
  Brain,
  Zap,
  Settings
} from "lucide-react";
import { useTranslation } from "../hooks/useTranslation";
import { 
  useAgents, 
  useAgentsByCategory, 
  useDashboardMetrics,
  usePerformanceMetrics,
  useAgentDisplayInfo,
  type ExtendedAgentResponse
} from "../hooks/api/useUnifiedApi";
import { AgentCategory } from "../types/unified";

const CATEGORY_COLORS = {
  initial_processing: '#3B82F6',
  orchestrator: '#8B5CF6', 
  specialized: '#10B981',
  alternative: '#F59E0B'
};

const CATEGORY_ICONS = {
  initial_processing: Target,
  orchestrator: Brain,
  specialized: Zap,
  alternative: Settings
};

export const MetricsVisualization = () => {
  const { t } = useTranslation();
  const { getAgentDisplayName } = useAgentDisplayInfo();
  
  // API calls using unified hooks
  const { data: allAgents, isLoading: agentsLoading } = useAgents();
  const { data: dashboardMetrics, isLoading: dashboardLoading } = useDashboardMetrics();
  const { data: performanceData, isLoading: performanceLoading } = usePerformanceMetrics();

  // Agent category data
  const { data: initialAgents } = useAgentsByCategory('initial_processing');
  const { data: orchestratorAgents } = useAgentsByCategory('orchestrator');
  const { data: specializedAgents } = useAgentsByCategory('specialized');
  const { data: alternativeAgents } = useAgentsByCategory('alternative');

  // Loading state
  if (agentsLoading || dashboardLoading || performanceLoading) {
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

  // Transform agent data by category
  const agentCategoryData = [
    { 
      name: 'Initial Processing', 
      count: initialAgents?.length || 0,
      active: initialAgents?.filter(a => a.status === 'active').length || 0,
      color: CATEGORY_COLORS.initial_processing
    },
    { 
      name: 'Orchestrator', 
      count: orchestratorAgents?.length || 0,
      active: orchestratorAgents?.filter(a => a.status === 'active').length || 0,
      color: CATEGORY_COLORS.orchestrator
    },
    { 
      name: 'Specialized', 
      count: specializedAgents?.length || 0,
      active: specializedAgents?.filter(a => a.status === 'active').length || 0,
      color: CATEGORY_COLORS.specialized
    },
    { 
      name: 'Alternative', 
      count: alternativeAgents?.length || 0,
      active: alternativeAgents?.filter(a => a.status === 'active').length || 0,
      color: CATEGORY_COLORS.alternative
    }
  ];

  // Transform performance data for charts
  const chartPerformanceData = performanceData?.throughputData?.map((item, index) => ({
    time: new Date(item.timestamp).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    }),
    throughput: item.value || 0,
    processing_time: performanceData.processingTimeData?.[index]?.value || 0
  })) || [];

  // Helper function to safely access agent metrics from API response
  const getAgentMetrics = (agent: ExtendedAgentResponse) => {
    // Access properties directly from the API agent response
    const agentWithMetrics = agent as ExtendedAgentResponse & {
      successRate?: number;
      throughput?: number;
      processingTime?: number;
      queueDepth?: number;
      llmUsage?: {
        totalTokens: number;
        promptTokens: number;
        completionTokens: number;
      };
    };
    
    return {
      success_rate: agentWithMetrics.successRate || 0,
      throughput_per_hour: agentWithMetrics.throughput || 0,
      processing_time_seconds: agentWithMetrics.processingTime || 0,
      queue_depth: agentWithMetrics.queueDepth || 0,
      llm_usage: agentWithMetrics.llmUsage || {
        totalTokens: 0,
        promptTokens: 0,
        completionTokens: 0
      }
    };
  };

  // Top performing agents - with proper null checks and correct property access
  const topAgents = allAgents?.slice(0, 8).map(agent => {
    const metrics = getAgentMetrics(agent);
    return {
      name: getAgentDisplayName(agent.name),
      category: agent.category,
      success_rate: metrics.success_rate,
      throughput: metrics.throughput_per_hour,
      processing_time: metrics.processing_time_seconds,
      color: CATEGORY_COLORS[agent.category]
    };
  }) || [];

  // Agent status distribution
  const statusData = allAgents ? [
    { name: 'Active', value: allAgents.filter(a => a.status === 'active').length, color: '#10B981' },
    { name: 'Processing', value: allAgents.filter(a => a.status === 'processing').length, color: '#3B82F6' },
    { name: 'Inactive', value: allAgents.filter(a => a.status === 'inactive').length, color: '#6B7280' },
    { name: 'Error', value: allAgents.filter(a => a.status === 'error').length, color: '#EF4444' }
  ] : [];

  // Helper function to safely get completed leads
  const getCompletedLeads = (): number => {
    if (!dashboardMetrics) return 0;
    
    // Type-safe access to completed leads with fallbacks
    const metricsData = dashboardMetrics as {
      completedLeads?: number;
      processedLeads?: number;
    };
    return metricsData.completedLeads || metricsData.processedLeads || 0;
  };

  // Helper function to safely get queue depth
  const getTotalQueueDepth = (): number => {
    if (!allAgents) return 0;
    return allAgents.reduce((sum, agent) => {
      const metrics = getAgentMetrics(agent);
      return sum + metrics.queue_depth;
    }, 0);
  };

  return (
    <div className="space-y-6">
      {/* Dashboard Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Users className="w-5 h-5 text-blue-400" />
              <div>
                <div className="text-2xl font-bold text-white">
                  {dashboardMetrics?.totalLeads || 0}
                </div>
                <div className="text-xs text-slate-400">{t('total_leads')}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Target className="w-5 h-5 text-green-400" />
              <div>
                <div className="text-2xl font-bold text-white">
                  {getCompletedLeads()}
                </div>
                <div className="text-xs text-slate-400">{t('completed')}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-purple-400" />
              <div>
                <div className="text-2xl font-bold text-white">
                  {allAgents?.filter(a => a.status === 'active').length || 0}
                </div>
                <div className="text-xs text-slate-400">{t('active_agents')}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-yellow-400" />
              <div>
                <div className="text-2xl font-bold text-white">
                  {dashboardMetrics?.successRate ? `${(dashboardMetrics.successRate * 100).toFixed(1)}%` : 'N/A'}
                </div>
                <div className="text-xs text-slate-400">{t('success_rate')}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Charts */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4 bg-slate-800">
          <TabsTrigger value="overview">{t('overview')}</TabsTrigger>
          <TabsTrigger value="agents">{t('agent_performance')}</TabsTrigger>
          <TabsTrigger value="categories">{t('categories')}</TabsTrigger>
          <TabsTrigger value="pipeline">{t('pipeline')}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-lg flex items-center">
                  <TrendingUp className="w-5 h-5 mr-2 text-green-500" />
                  {t('performance_trends')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
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
                    <Line type="monotone" dataKey="throughput" stroke="#10B981" strokeWidth={2} name="Throughput" />
                    <Line type="monotone" dataKey="processing_time" stroke="#3B82F6" strokeWidth={2} name="Processing Time" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-lg flex items-center">
                  <Activity className="w-5 h-5 mr-2 text-blue-500" />
                  {t('agent_status_distribution')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={statusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {statusData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-2 gap-2 mt-4">
                  {statusData.map((item) => (
                    <div key={item.name} className="flex items-center space-x-2">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-sm text-slate-300">{item.name}: {item.value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="agents" className="space-y-4">
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg flex items-center">
                <Target className="w-5 h-5 mr-2 text-blue-500" />
                {t('top_agent_performance')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={topAgents}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="name" 
                    stroke="#9CA3AF" 
                    angle={-45}
                    textAnchor="end"
                    height={100}
                  />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="success_rate" fill="#10B981" name="Success Rate %" />
                  <Bar dataKey="throughput" fill="#3B82F6" name="Throughput/hr" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="categories" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(CATEGORY_COLORS).map(([category, color]) => {
              const categoryData = agentCategoryData.find(c => c.name.toLowerCase().includes(category.split('_')[0]));
              const Icon = CATEGORY_ICONS[category as AgentCategory];
              
              return (
                <Card key={category} className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <Icon className="w-6 h-6" style={{ color }} />
                      <Badge 
                        variant="outline" 
                        className="text-xs"
                        style={{ borderColor: color, color }}
                      >
                        {categoryData?.active || 0}/{categoryData?.count || 0}
                      </Badge>
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-white font-medium capitalize">
                        {category.replace('_', ' ')}
                      </h3>
                      <div className="text-2xl font-bold text-white">
                        {categoryData?.count || 0}
                      </div>
                      <div className="text-xs text-slate-400">
                        Active: {categoryData?.active || 0}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg flex items-center">
                <Brain className="w-5 h-5 mr-2 text-purple-500" />
                {t('agent_categories_overview')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={agentCategoryData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                  />
                  <Bar dataKey="count" fill="#6B7280" name="Total Agents" />
                  <Bar dataKey="active" fill="#10B981" name="Active Agents" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="pipeline" className="space-y-4">
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg flex items-center">
                <Clock className="w-5 h-5 mr-2 text-yellow-500" />
                {t('pipeline_performance')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-400">
                    {dashboardMetrics?.averageProcessingTime?.toFixed(1) || 'N/A'}s
                  </div>
                  <div className="text-sm text-slate-400">{t('average_processing_time')}</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-blue-400">
                    {allAgents?.filter(a => a.status === 'processing').length || 0}
                  </div>
                  <div className="text-sm text-slate-400">{t('currently_processing')}</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-purple-400">
                    {getTotalQueueDepth()}
                  </div>
                  <div className="text-sm text-slate-400">{t('queue_depth')}</div>
                </div>
              </div>
              
              <div className="space-y-3">
                <h4 className="text-white font-medium">{t('pipeline_stages')}</h4>
                {allAgents?.slice(0, 5).map((agent) => {
                  const metrics = getAgentMetrics(agent);
                  return (
                    <div key={agent.id} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div 
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: CATEGORY_COLORS[agent.category] }}
                        />
                        <span className="text-white text-sm">{getAgentDisplayName(agent.name)}</span>
                        <Badge variant="outline" className="text-xs">
                          {agent.category.replace('_', ' ')}
                        </Badge>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-white">
                          {metrics.processing_time_seconds.toFixed(1)}s
                        </div>
                        <div className="text-xs text-slate-400">{agent.status}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};
