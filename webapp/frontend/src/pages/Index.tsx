import { useState, useEffect } from 'react';
import { TranslationProvider, useTranslation } from '../hooks/useTranslation';
import { useAgents, useLeads, useDashboardMetrics, useBusinessContext, useStartProspectingJob } from '../hooks/api/useUnifiedApi';
import { useRealTimeUpdates } from '../hooks/useRealTimeUpdates';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Bot,
  TrendingUp,
  Users,
  MessageSquare,
  Settings,
  Globe,
  Activity,
  BarChart3,
  Zap,
  Kanban,
  Rocket
} from "lucide-react";

import { ProspectDashboard } from '../components/ProspectDashboard';
import { AgentStatusCard } from '../components/AgentStatusCard';
import { LeadCard } from '../components/LeadCard';
import { ChatInterface } from '../components/ChatInterface';
import { BusinessContextForm } from '../components/BusinessContextForm';
import { BusinessContextCenter } from '../components/BusinessContextCenter';
import { MetricsVisualization } from '../components/MetricsVisualization';
import { CRMBoard } from '../components/CRMBoard';
import { ConnectionStatus } from '../components/ConnectionStatus';
import { AgentsEmptyState } from '../components/EmptyStates/AgentsEmptyState';
import { LeadsEmptyState } from '../components/EmptyStates/LeadsEmptyState';
import { WebSocketProvider } from '../contexts/WebSocketContext';

import {
  AgentStatus,
  LeadData,
  AgentName,
  AgentCategory,
  AgentStatusType,
  DashboardMetrics,
  ExtendedAgentResponse
} from '../types/unified';
import { Language } from '../i18n/translations';
import { LeadResponse, AgentResponse, DashboardMetricsResponse } from '../types/api'; // Restored LeadResponse and AgentResponse for transformers

// Helper function to provide default metrics structure, matching DashboardMetricsResponse
const getDefaultFrontendMetrics = (): DashboardMetricsResponse => ({
  totalLeads: 0,
  totalAgents: 0,
  activeAgents: 0,
  processingRate: 0,
  successRate: 0,
  recentActivity: [],
  lastUpdated: new Date().toISOString(),
});

// Helper function to transform API response to frontend types

// Copied from unified.ts for AGENT_DISPLAY_NAMES
export const AGENT_DISPLAY_NAMES: Record<AgentName, string> = {
  'lead_intake_agent': 'Lead Intake Agent',
  'lead_analysis_agent': 'Lead Analysis Agent',
  'enhanced_lead_processor': 'Enhanced Lead Processor',
  'tavily_enrichment_agent': 'Web Research Agent',
  'contact_extraction_agent': 'Contact Extraction Agent',
  'pain_point_deepening_agent': 'Pain Point Analysis Agent',
  'lead_qualification_agent': 'Lead Qualification Agent',
  'competitor_identification_agent': 'Competitor Analysis Agent',
  'strategic_question_generation_agent': 'Strategic Questions Agent',
  'buying_trigger_identification_agent': 'Buying Triggers Agent',
  'tot_strategy_generation_agent': 'Strategy Generation Agent',
  'tot_strategy_evaluation_agent': 'Strategy Evaluation Agent',
  'tot_action_plan_synthesis_agent': 'Action Plan Synthesis Agent',
  'detailed_approach_plan_agent': 'Approach Planning Agent',
  'objection_handling_agent': 'Objection Handling Agent',
  'value_proposition_customization_agent': 'Value Proposition Agent',
  'b2b_personalized_message_agent': 'Message Personalization Agent',
  'internal_briefing_summary_agent': 'Internal Briefing Agent',
  'approach_strategy_agent': 'Approach Strategy Agent',
  'b2b_persona_creation_agent': 'B2B Persona Agent',
  'message_crafting_agent': 'Message Crafting Agent',
  'persona_creation_agent': 'Persona Creation Agent',
  'lead_analysis_generation_agent': 'Analysis Generation Agent'
};
// End copied AGENT_DISPLAY_NAMES

const transformLeadResponse = (apiLead: LeadResponse): LeadData => ({
  id: apiLead.id,
  company_name: apiLead.company_name,
  website: apiLead.website,
  relevance_score: apiLead.relevance_score,
  roi_potential_score: apiLead.roi_potential_score,
  qualification_tier: apiLead.qualification_tier,
  company_sector: apiLead.company_sector,
  persona: apiLead.persona,
  pain_point_analysis: apiLead.pain_point_analysis,
  purchase_triggers: apiLead.purchase_triggers,
  processing_stage: apiLead.processing_stage,
  created_at: apiLead.created_at,
  updated_at: apiLead.updated_at,
  status: apiLead.status,
  enrichment_data: apiLead.enrichment_data
});

// Helper function to transform Agent API response to frontend types
const transformAgentResponse = (apiAgent: AgentResponse): AgentStatus => {
  // Assuming apiAgent.name is a string that should match one of AgentName
  // and apiAgent.category is a string that should match one of AgentCategory
  // The AgentResponse type from types/api.ts should ideally reflect this.
  const agentName = apiAgent.name as AgentName;
  // Cast, assuming API provides valid names
  const agentCategory = (apiAgent.category || 'specialized') as AgentCategory; // Default category if undefined

  return {
    id: apiAgent.id,
    name: agentName,
    status: apiAgent.status as AgentStatusType, // Cast status
    displayName: AGENT_DISPLAY_NAMES[agentName] || apiAgent.name, // Use display name map or fallback to name
    description: apiAgent.description || `Details for ${apiAgent.name}`, // Fallback description
    category: agentCategory,
    current_task: apiAgent.currentTask,
    metrics: {
      processing_time_seconds: apiAgent.processingTime ?? 0,
      llm_usage: {
        total_tokens: apiAgent.llmTokenUsage ?? 0,
        prompt_tokens: Math.floor((apiAgent.llmTokenUsage ?? 0) * 0.5),
        completion_tokens: Math.floor((apiAgent.llmTokenUsage ?? 0) * 0.5)
      },
      success_rate: apiAgent.successRate ?? 0,
      queue_depth: apiAgent.queueDepth ?? 0,
      throughput_per_hour: apiAgent.throughput ?? 0
    },
    last_updated: apiAgent.updatedAt || new Date().toISOString()
  };
};

const DashboardContent = () => {
  const { t, language, setLanguage } = useTranslation();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showBusinessContextForm, setShowBusinessContextForm] = useState(false);

  // Initialize real-time updates
  useRealTimeUpdates();

  // API calls
  const { data: agentsData, isLoading: agentsLoading, error: agentsError } = useAgents();
  const { data: leadsResponse, isLoading: leadsLoading, error: leadsError } = useLeads();
  const { data: metricsData, isLoading: metricsLoading, error: metricsError } = useDashboardMetrics();
  const { data: businessContext, isLoading: businessContextLoading, isError: businessContextError, isSuccess: businessContextSuccess } = useBusinessContext();
  const startProspectingMutation = useStartProspectingJob();

  const handleContextSetupComplete = () => {
    setShowBusinessContextForm(false);
    // Optionally, you can force a refetch of data here if needed
  };

  const handleStartHarvesting = () => {
    if (businessContext) {
      startProspectingMutation.mutate(businessContext);
    }
  };

  // Show loading state
  if (agentsLoading || leadsLoading || metricsLoading || businessContextLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-green-950 flex items-center justify-center">
        <div className="text-white text-xl">{t('loading')}</div>
      </div>
    );
  }

  // Show error state
  if (agentsError || leadsError || metricsError || businessContextError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-green-950 flex items-center justify-center">
        <div className="text-red-400 text-xl">{t('error_loading_data')}</div>
      </div>
    );
  }

  // Onboarding Flow for new users: show if the context query is successful but there's no context.
  if (businessContextSuccess && !businessContext) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-green-950 flex items-center justify-center">
        <Card className="p-8 bg-slate-800 border-slate-700 text-white text-center max-w-lg">
          {!showBusinessContextForm ? (
            <>
              <Zap size={48} className="mx-auto mb-4 text-green-500" />
              <h2 className="text-2xl font-bold mb-4">{t('welcome_nellia')}</h2>
              <p className="mb-6 text-slate-300">
                {t('first_time_message')}
              </p>
              <Button onClick={() => setShowBusinessContextForm(true)} className="bg-green-600 hover:bg-green-700">
                {t('setup_business_context')}
              </Button>
            </>
          ) : (
            <BusinessContextForm onComplete={handleContextSetupComplete} />
          )}
        </Card>
      </div>
    );
  }

  if (businessContextSuccess && businessContext) {
    const agents: AgentStatus[] = Array.isArray(agentsData) ? agentsData.map(transformAgentResponse) : [];
    const leads: LeadData[] = leadsResponse?.data ? leadsResponse.data.map(transformLeadResponse) : [];
    const metrics: DashboardMetricsResponse = metricsData || getDefaultFrontendMetrics();

    const handleLeadUpdate = (updatedLead: LeadData) => {
      console.log('Lead updated:', updatedLead);
    };

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-green-950">
        {/* Header */}
        <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <Zap className="w-8 h-8 text-green-500" />
                  <div>
                    <h1 className="text-2xl font-bold text-white">Nellia Prospector</h1>
                    <p className="text-sm text-green-400">AI-Powered B2B Lead Processing</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Connection Status */}
              <ConnectionStatus showText={false} className="mr-2" />
              
              <Select value={language} onValueChange={(value: Language) => setLanguage(value)}>
                <SelectTrigger className="w-32 bg-slate-800 border-slate-700 text-white">
                  <Globe className="w-4 h-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700 text-white">
                  <SelectItem value="pt">Português</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="es">Español</SelectItem>
                </SelectContent>
              </Select>
              
              <Badge variant="outline" className="bg-green-600/20 text-green-400 border-green-600">
                {t('real_time_active')}
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid grid-cols-7 bg-slate-800 border border-slate-700">
            <TabsTrigger value="dashboard" className="text-white data-[state=active]:bg-slate-700">
              <BarChart3 className="w-4 h-4 mr-2" />
              {t('dashboard')}
            </TabsTrigger>
            <TabsTrigger value="prospect" className="text-white data-[state=active]:bg-slate-700">
               <Rocket className="w-4 h-4 mr-2" />
               {t('prospect')}
            </TabsTrigger>
            <TabsTrigger value="crm" className="text-white data-[state=active]:bg-slate-700">
              <Kanban className="w-4 h-4 mr-2" />
              {t('crm_board')}
            </TabsTrigger>
            <TabsTrigger value="agents" className="text-white data-[state=active]:bg-slate-700">
              <Bot className="w-4 h-4 mr-2" />
              {t('agents')}
            </TabsTrigger>
            <TabsTrigger value="leads" className="text-white data-[state=active]:bg-slate-700">
              <Users className="w-4 h-4 mr-2" />
              {t('leads')}
            </TabsTrigger>
            <TabsTrigger value="chat" className="text-white data-[state=active]:bg-slate-700">
              <MessageSquare className="w-4 h-4 mr-2" />
              {t('chat')}
            </TabsTrigger>
            <TabsTrigger value="context" className="text-white data-[state=active]:bg-slate-700">
              <Settings className="w-4 h-4 mr-2" />
              {t('contexto')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="bg-gradient-to-br from-green-900 to-green-800 border-green-700">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-lg flex items-center">
                    <TrendingUp className="w-5 h-5 mr-2" />
                    {t('success_rate_title')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-white">{metrics.successRate.toFixed(1)}%</div>
                  <p className="text-green-200 text-sm">{t('completed_leads')}</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-blue-900 to-blue-800 border-blue-700">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-lg flex items-center">
                    <Users className="w-5 h-5 mr-2" />
                    {t('total_leads_title')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-white">{metrics.totalLeads}</div>
                  <p className="text-blue-200 text-sm">{t('in_system')}</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-purple-900 to-purple-800 border-purple-700">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-lg flex items-center">
                    <Activity className="w-5 h-5 mr-2" />
                    {t('agents_title')}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-white">{metrics.activeAgents}/{metrics.totalAgents}</div>
                  <p className="text-purple-200 text-sm">{t('active_total')}</p>
                </CardContent>
              </Card>
            </div>

              <MetricsVisualization />

              <Card className="md:col-span-3 bg-slate-800/50 border-slate-700">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-lg font-medium text-white">
                        {t('automated_prospecting')}
                    </CardTitle>
                    <Zap className="w-5 h-5 text-green-500" />
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-slate-400 mb-4">
                        {t('automated_prospecting_desc')}
                    </p>
                    <Button
                        onClick={handleStartHarvesting}
                        disabled={!businessContext || startProspectingMutation.isPending}
                        className="w-full bg-green-600 hover:bg-green-700 disabled:bg-slate-600 disabled:cursor-not-allowed"
                    >
                        {startProspectingMutation.isPending ? t('harvesting_progress') : t('start_new_harvest')}
                    </Button>
                    {startProspectingMutation.isError && (
                        <p className="text-red-400 text-sm mt-2">
                            {t('error_starting_harvesting')} {startProspectingMutation.error.message}
                        </p>
                    )}
                </CardContent>
              </Card>
        
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:col-span-3">
              {agents.slice(0, 3).map((agent) => (
                <AgentStatusCard key={agent.id} agent={agent} showControls={false} />
              ))}
            </div>
          </TabsContent>

          <TabsContent value="prospect">
            <ProspectDashboard />
          </TabsContent>

          <TabsContent value="crm" className="space-y-6">
            <CRMBoard leads={leads} onLeadUpdate={handleLeadUpdate} />
          </TabsContent>

          <TabsContent value="agents" className="space_y-6">
            {agentsLoading && <p className="text-white">{t('loading_agents')}</p>}
            {!agentsLoading && agentsError && <p className="text-red-400">{t('error_loading_agents')}</p>}
            {!agentsLoading && !agentsError && agents.length === 0 && (
              <AgentsEmptyState />
            )}
            {!agentsLoading && !agentsError && agents.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {agents.map((agent) => (
                  <AgentStatusCard key={agent.id} agent={agent} showControls={false} />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="leads" className="space-y-6">
            {leadsLoading && <p className="text-white">{t('loading_leads')}</p>}
            {!leadsLoading && leadsError && <p className="text-red-400">{t('error_loading_leads')}</p>}
            {!leadsLoading && !leadsError && leads.length === 0 && (
              // TODO: The onStartProspecting function needs to be defined.
              // For now, it will be a console log.
              <LeadsEmptyState onStartProspecting={() => console.log('Start Prospecting clicked')} />
            )}
            {!leadsLoading && !leadsError && leads.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {leads.map((lead) => (
                  <LeadCard key={lead.id} lead={lead} />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="chat">
            <ChatInterface />
          </TabsContent>

          <TabsContent value="context">
            <BusinessContextCenter />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};
}


const Index = () => {
  return (
    <WebSocketProvider>
      <TranslationProvider>
        <DashboardContent />
      </TranslationProvider>
    </WebSocketProvider>
  );
};

export default Index;
