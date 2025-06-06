import { useState, useEffect } from 'react';
import { TranslationProvider, useTranslation } from '../hooks/useTranslation';
import { useAgents, useLeads, useDashboardMetrics, useBusinessContext } from '../hooks/api';
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
  Kanban
} from "lucide-react";

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
// Placeholder for OnboardingFlow, to be created in Phase 2
// import { OnboardingFlow } from '../components/OnboardingFlow'; 

import { 
  AgentStatus, 
  LeadData, 
  // DashboardMetricsData, // Will be replaced by DashboardMetricsResponse from nellia
  AgentName,
  AgentCategory,
  AgentStatusType,
  DashboardMetricsResponse, // Import the new structure from nellia.ts
  RecentActivityItem // Import if needed by new metrics structure
} from '../types/nellia'; 
import { Language } from '../i18n/translations';
import { LeadResponse, AgentResponse } from '../types/api'; // Restored LeadResponse and AgentResponse for transformers

// Helper function to provide default metrics structure, matching new DashboardMetricsResponse
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
  company_name: apiLead.companyName,
  website: apiLead.website,
  relevance_score: apiLead.relevanceScore,
  roi_potential_score: apiLead.roiPotential,
  brazilian_market_fit: apiLead.brazilianMarketFit,
  qualification_tier: apiLead.qualificationTier === 'A' ? 'High Potential' : 
                     apiLead.qualificationTier === 'B' ? 'Medium Potential' : 'Low Potential',
  company_sector: apiLead.sector,
  persona: {
    likely_role: apiLead.likelyContactRole,
    decision_maker_probability: apiLead.decisionMakerProbability
  },
  pain_point_analysis: apiLead.painPoints,
  purchase_triggers: apiLead.triggers,
  processing_stage: apiLead.processingStage as LeadData['processing_stage'],
  created_at: apiLead.createdAt,
  updated_at: apiLead.updatedAt
});

// Helper function to transform Agent API response to frontend types
const transformAgentResponse = (apiAgent: AgentResponse): AgentStatus => {
  // Assuming apiAgent.name is a string that should match one of AgentName
  // and apiAgent.category is a string that should match one of AgentCategory
  // The AgentResponse type from types/api.ts should ideally reflect this.
  const agentName = apiAgent.name as AgentName; // Cast, assuming API provides valid names
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

// Mock data - updated to conform to AgentStatus type
const mockAgents: AgentStatus[] = [
  {
    id: '1',
    name: 'lead_intake_agent', // Valid AgentName
    displayName: AGENT_DISPLAY_NAMES['lead_intake_agent'],
    category: 'initial_processing', // Valid AgentCategory
    status: 'active',
    current_task: 'Processing TechCorp lead data',
    metrics: { processing_time_seconds: 2.3, llm_usage: { total_tokens: 45230, prompt_tokens: 23400, completion_tokens: 21830 }, success_rate: 0.98, queue_depth: 3, throughput_per_hour: 67 },
    last_updated: new Date().toISOString(),
    description: 'Intakes and performs initial validation of leads.'
  },
  {
    id: '2',
    name: 'lead_analysis_agent', // Valid AgentName
    displayName: AGENT_DISPLAY_NAMES['lead_analysis_agent'],
    category: 'initial_processing', // Valid AgentCategory
    status: 'processing',
    current_task: 'Analyzing market fit for Inovacorp',
    metrics: { processing_time_seconds: 1.8, llm_usage: { total_tokens: 52100, prompt_tokens: 28900, completion_tokens: 23200 }, success_rate: 0.94, queue_depth: 1, throughput_per_hour: 89 },
    last_updated: new Date().toISOString(),
    description: 'Analyzes lead data for deeper insights.'
  },
  {
    id: '3',
    name: 'persona_creation_agent', // Valid AgentName
    displayName: AGENT_DISPLAY_NAMES['persona_creation_agent'],
    category: 'specialized', // Valid AgentCategory
    status: 'completed',
    current_task: '',
    metrics: { processing_time_seconds: 2.1, llm_usage: { total_tokens: 38700, prompt_tokens: 19400, completion_tokens: 19300 }, success_rate: 0.96, queue_depth: 0, throughput_per_hour: 54 },
    last_updated: new Date().toISOString(),
    description: 'Creates detailed buyer personas.'
  },
  {
    id: '4',
    name: 'approach_strategy_agent', // Valid AgentName
    displayName: AGENT_DISPLAY_NAMES['approach_strategy_agent'],
    category: 'alternative', // Valid AgentCategory
    status: 'inactive',
    current_task: '',
    metrics: { processing_time_seconds: 2.7, llm_usage: { total_tokens: 41200, prompt_tokens: 22100, completion_tokens: 19100 }, success_rate: 0.92, queue_depth: 0, throughput_per_hour: 43 },
    last_updated: new Date().toISOString(),
    description: 'Develops strategic approach plans.'
  },
  {
    id: '5',
    name: 'message_crafting_agent', // Valid AgentName
    displayName: AGENT_DISPLAY_NAMES['message_crafting_agent'],
    category: 'alternative', // Valid AgentCategory
    status: 'inactive',
    current_task: '',
    metrics: { processing_time_seconds: 1.9, llm_usage: { total_tokens: 36800, prompt_tokens: 18900, completion_tokens: 17900 }, success_rate: 0.97, queue_depth: 0, throughput_per_hour: 38 },
    last_updated: new Date().toISOString(),
    description: 'Crafts personalized messages for leads.'
  }
];

const mockLeads: LeadData[] = [
  {
    id: '1',
    company_name: 'TechCorp Brasil',
    website: 'techcorp.com.br',
    relevance_score: 0.89,
    roi_potential_score: 0.76,
    brazilian_market_fit: 0.92,
    qualification_tier: 'High Potential',
    company_sector: 'SaaS B2B',
    persona: {
      likely_role: 'CTO',
      decision_maker_probability: 0.87
    },
    pain_point_analysis: ['Escalabilidade', 'Integração de sistemas', 'Automação de processos'],
    purchase_triggers: ['Crescimento de 200%', 'Expansão para novos mercados'],
      processing_stage: 'prospecting',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: '2',
    company_name: 'InovaCorp',
    website: 'inovacorp.com.br',
    relevance_score: 0.72,
    roi_potential_score: 0.68,
    brazilian_market_fit: 0.85,
    qualification_tier: 'Medium Potential',
    company_sector: 'E-commerce',
    persona: {
      likely_role: 'Head de Marketing',
      decision_maker_probability: 0.64
    },
    processing_stage: 'analyzing_refining',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  },
  {
    id: '3',
    company_name: 'FinTech Solutions',
    website: 'fintechsol.com.br',
    relevance_score: 0.94,
    roi_potential_score: 0.88,
    brazilian_market_fit: 0.96,
    qualification_tier: 'High Potential',
    company_sector: 'Fintech',
    persona: {
      likely_role: 'CEO',
      decision_maker_probability: 0.95
    },
    processing_stage: 'reuniao_agendada',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }
];

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
  const { data: businessContext, isLoading: businessContextLoading, error: businessContextError } = useBusinessContext();

  const agents: AgentStatus[] = Array.isArray(agentsData) ? agentsData.map(transformAgentResponse) : [];
  const leads: LeadData[] = leadsResponse?.data ? leadsResponse.data.map(transformLeadResponse) : [];
  const metrics: DashboardMetricsResponse = metricsData || getDefaultFrontendMetrics();

  // Determine if the user needs to go through onboarding.
  const isNewUser = !businessContext && !businessContextLoading;

  const handleLeadUpdate = (updatedLead: LeadData) => {
    console.log('Lead updated:', updatedLead);
  };

  const handleContextSetupComplete = () => {
    setShowBusinessContextForm(false);
    // Optionally, you can force a refetch of data here if needed
  };

  // Show loading state
  if (agentsLoading || leadsLoading || metricsLoading || businessContextLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-green-950 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  // Show error state
  if (agentsError || leadsError || metricsError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-green-950 flex items-center justify-center">
        <div className="text-red-400 text-xl">Error loading data. Please try again later.</div>
      </div>
    );
  }

  // Onboarding Flow for new users
  if (isNewUser) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-green-950 flex items-center justify-center">
        <Card className="p-8 bg-slate-800 border-slate-700 text-white text-center max-w-lg">
          {!showBusinessContextForm ? (
            <>
              <Zap size={48} className="mx-auto mb-4 text-green-500" />
              <h2 className="text-2xl font-bold mb-4">Bem-vindo ao Nellia Prospector!</h2>
              <p className="mb-6 text-slate-300">
                Parece que é sua primeira vez aqui.
                <br />
                Vamos configurar seu contexto de negócios para começar a encontrar leads.
              </p>
              <Button onClick={() => setShowBusinessContextForm(true)} className="bg-green-600 hover:bg-green-700">
                Configurar Contexto de Negócios
              </Button>
            </>
          ) : (
            <BusinessContextForm onComplete={handleContextSetupComplete} />
          )}
        </Card>
      </div>
    );
  }

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
                Real-time Active
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid grid-cols-6 bg-slate-800 border border-slate-700">
            <TabsTrigger value="dashboard" className="text-white data-[state=active]:bg-slate-700">
              <BarChart3 className="w-4 h-4 mr-2" />
              {t('dashboard')}
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
              Contexto
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="bg-gradient-to-br from-green-900 to-green-800 border-green-700">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-lg flex items-center">
                    <TrendingUp className="w-5 h-5 mr-2" />
                    Taxa de Sucesso
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-white">{metrics.successRate.toFixed(1)}%</div>
                  <p className="text-green-200 text-sm">De leads concluídos</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-blue-900 to-blue-800 border-blue-700">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-lg flex items-center">
                    <Users className="w-5 h-5 mr-2" />
                    Total de Leads
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-white">{metrics.totalLeads}</div>
                  <p className="text-blue-200 text-sm">No sistema</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-purple-900 to-purple-800 border-purple-700">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-lg flex items-center">
                    <Activity className="w-5 h-5 mr-2" />
                    Agentes
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-white">{metrics.activeAgents}/{metrics.totalAgents}</div>
                  <p className="text-purple-200 text-sm">Ativos / Total</p>
                </CardContent>
              </Card>
            </div>

            <MetricsVisualization />

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.slice(0, 3).map((agent) => (
                <AgentStatusCard key={agent.id} agent={agent} />
              ))}
            </div>
          </TabsContent>

          <TabsContent value="crm" className="space-y-6">
            <CRMBoard leads={leads} onLeadUpdate={handleLeadUpdate} />
          </TabsContent>

          <TabsContent value="agents" className="space_y-6">
            {agentsLoading && <p className="text-white">Loading agents...</p>}
            {!agentsLoading && agentsError && <p className="text-red-400">Error loading agents.</p>}
            {!agentsLoading && !agentsError && agents.length === 0 && (
              <AgentsEmptyState />
            )}
            {!agentsLoading && !agentsError && agents.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {agents.map((agent) => (
                  <AgentStatusCard key={agent.id} agent={agent} />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="leads" className="space-y-6">
            {leadsLoading && <p className="text-white">Loading leads...</p>}
            {!leadsLoading && leadsError && <p className="text-red-400">Error loading leads.</p>}
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

const Index = () => {
  return (
    <TranslationProvider>
      <DashboardContent />
    </TranslationProvider>
  );
};

export default Index;
