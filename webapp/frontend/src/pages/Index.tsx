import { useState } from 'react';
import { TranslationProvider, useTranslation } from '../hooks/useTranslation';
import { useAgents, useLeads, useDashboardMetrics } from '../hooks/api';
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
import { BusinessContextCenter } from '../components/BusinessContextCenter';
import { MetricsVisualization } from '../components/MetricsVisualization';
import { CRMBoard } from '../components/CRMBoard';

import { AgentStatus, LeadData } from '../types/nellia';
import { Language } from '../i18n/translations';
import { LeadResponse, AgentResponse } from '../types/api';

// Helper function to transform API response to frontend types
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
const transformAgentResponse = (apiAgent: AgentResponse): AgentStatus => ({
  id: apiAgent.id,
  name: apiAgent.name,
  status: apiAgent.status,
  current_task: apiAgent.currentTask,
  metrics: {
    processing_time_seconds: apiAgent.processingTime,
    llm_usage: {
      total_tokens: apiAgent.llmTokenUsage,
      prompt_tokens: Math.floor(apiAgent.llmTokenUsage * 0.5), // Estimated
      completion_tokens: Math.floor(apiAgent.llmTokenUsage * 0.5) // Estimated
    },
    success_rate: apiAgent.successRate,
    queue_depth: apiAgent.queueDepth,
    throughput_per_hour: apiAgent.throughput
  },
  last_updated: apiAgent.updatedAt
});

// Mock data
const mockAgents: AgentStatus[] = [
  {
    id: '1',
    name: 'lead_intake',
    status: 'active',
    current_task: 'Processing TechCorp lead data',
    metrics: {
      processing_time_seconds: 2.3,
      llm_usage: { total_tokens: 45230, prompt_tokens: 23400, completion_tokens: 21830 },
      success_rate: 0.98,
      queue_depth: 3,
      throughput_per_hour: 67
    },
    last_updated: new Date().toISOString()
  },
  {
    id: '2',
    name: 'analysis',
    status: 'processing',
    current_task: 'Analyzing market fit for Inovacorp',
    metrics: {
      processing_time_seconds: 1.8,
      llm_usage: { total_tokens: 52100, prompt_tokens: 28900, completion_tokens: 23200 },
      success_rate: 0.94,
      queue_depth: 1,
      throughput_per_hour: 89
    },
    last_updated: new Date().toISOString()
  },
  {
    id: '3',
    name: 'persona_creation',
    status: 'completed',
    current_task: '',
    metrics: {
      processing_time_seconds: 2.1,
      llm_usage: { total_tokens: 38700, prompt_tokens: 19400, completion_tokens: 19300 },
      success_rate: 0.96,
      queue_depth: 0,
      throughput_per_hour: 54
    },
    last_updated: new Date().toISOString()
  },
  {
    id: '4',
    name: 'approach_strategy',
    status: 'inactive',
    current_task: '',
    metrics: {
      processing_time_seconds: 2.7,
      llm_usage: { total_tokens: 41200, prompt_tokens: 22100, completion_tokens: 19100 },
      success_rate: 0.92,
      queue_depth: 0,
      throughput_per_hour: 43
    },
    last_updated: new Date().toISOString()
  },
  {
    id: '5',
    name: 'message_crafting',
    status: 'inactive',
    current_task: '',
    metrics: {
      processing_time_seconds: 1.9,
      llm_usage: { total_tokens: 36800, prompt_tokens: 18900, completion_tokens: 17900 },
      success_rate: 0.97,
      queue_depth: 0,
      throughput_per_hour: 38
    },
    last_updated: new Date().toISOString()
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

  // API calls
  const { data: agentsData = [], isLoading: agentsLoading, error: agentsError } = useAgents();
  const { data: leadsResponse, isLoading: leadsLoading, error: leadsError } = useLeads();
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useDashboardMetrics();

  // Transform API data to frontend types
  const agents = agentsData.map(transformAgentResponse);
  const leads = leadsResponse?.data?.map(transformLeadResponse) || [];

  const handleLeadUpdate = (updatedLead: LeadData) => {
    // This will be handled by React Query mutations
    console.log('Lead updated:', updatedLead);
  };

  // Show loading state
  if (agentsLoading || leadsLoading || metricsLoading) {
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
              
              {/* <Badge variant="outline" className="bg-green-600/20 text-green-400 border-green-600">
                527% ROI Average
              </Badge> */}
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
                    Total ROI
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-white">527%</div>
                  <p className="text-green-200 text-sm">Média dos últimos 30 dias</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-blue-900 to-blue-800 border-blue-700">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-lg flex items-center">
                    <Users className="w-5 h-5 mr-2" />
                    Leads Processados
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-white">1,234</div>
                  <p className="text-blue-200 text-sm">Últimas 24 horas</p>
                </CardContent>
              </Card>

              <Card className="bg-gradient-to-br from-purple-900 to-purple-800 border-purple-700">
                <CardHeader className="pb-3">
                  <CardTitle className="text-white text-lg flex items-center">
                    <Activity className="w-5 h-5 mr-2" />
                    Agentes Ativos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-white">5/5</div>
                  <p className="text-purple-200 text-sm">Sistema 100% operacional</p>
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

          <TabsContent value="agents" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map((agent) => (
                <AgentStatusCard key={agent.id} agent={agent} />
              ))}
            </div>
          </TabsContent>

          <TabsContent value="leads" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {leads.map((lead) => (
                <LeadCard key={lead.id} lead={lead} />
              ))}
            </div>
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
