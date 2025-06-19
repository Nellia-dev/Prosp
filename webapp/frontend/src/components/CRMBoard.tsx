import { useState, useMemo, useEffect } from 'react';
import { useRealTimeUpdates, useRealTimeEvent } from '../hooks/useRealTimeUpdates';
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { CompactLeadCard } from './CompactLeadCard';
import { LeadDetailsModal } from './LeadDetailsModal';
import { 
  LeadData, 
  ProcessingStage, 
  PROCESSING_STAGES, 
  STAGE_DISPLAY_NAMES, 
  STAGE_COLORS,
  QualificationTier 
} from '../types/unified';
import { 
  LeadCreatedEvent, 
  LeadEnrichedEvent, 
  ProspectPipelineEvent,
  isProspectPipelineEvent 
} from '../types/events';
import { useTranslation } from '../hooks/useTranslation';
import { useUpdateLeadStage } from '../hooks/api/useUnifiedApi';
import { Search, RotateCcw, RefreshCw, TrendingUp, Users, Target } from 'lucide-react';

interface CRMBoardProps {
  leads: LeadData[];
  onLeadUpdate?: (lead: LeadData) => void;
  onNewLead?: (lead: LeadData) => void; // Add this to handle new leads from websockets
  isLoading?: boolean;
}

// Create a proper enrichment event interface that aligns with our use case
interface EnrichmentEvent {
  event_type: string;
  lead_id: string;
  status_message?: string;
  agent_name?: string;
}

const STAGE_CONFIGS = PROCESSING_STAGES.map(stage => ({
  id: stage,
  label: STAGE_DISPLAY_NAMES[stage],
  color: STAGE_COLORS[stage] || '#6b7280', // Fallback to gray
  bgClass: 'border-l-4',
  style: { borderLeftColor: STAGE_COLORS[stage] || '#6b7280' }
}));

export const CRMBoard = ({ leads, onLeadUpdate, onNewLead, isLoading = false }: CRMBoardProps) => {
  const { t } = useTranslation();
  
  const [enrichmentEvents, setEnrichmentEvents] = useState<Record<string, EnrichmentEvent>>({});
  const [draggedLead, setDraggedLead] = useState<LeadData | null>(null);
  const [selectedLead, setSelectedLead] = useState<LeadData | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [recentlyUpdated, setRecentlyUpdated] = useState<Record<string, boolean>>({});
  const [filters, setFilters] = useState({
    search: '',
    sector: 'all',
    qualification: 'all',
    scoreRange: 'all'
  });

  const updateLeadStageMutation = useUpdateLeadStage();

  useEffect(() => {
    if (leads.length > 0) {
      const latestLead = leads.reduce((a, b) => new Date(a.updated_at) > new Date(b.updated_at) ? a : b);
      setRecentlyUpdated(prev => ({ ...prev, [latestLead.id]: true }));
      const timer = setTimeout(() => {
        setRecentlyUpdated(prev => ({ ...prev, [latestLead.id]: false }));
      }, 5000); // Glow for 5 seconds
      return () => clearTimeout(timer);
    }
  }, [leads]);

  useRealTimeEvent<LeadCreatedEvent>('lead-created', (event) => {
    if (onNewLead) {
      onNewLead(event.lead);
    }
  });

  useRealTimeEvent<ProspectPipelineEvent>('enrichment-update', (event) => {
    if (isProspectPipelineEvent(event) && 'lead_id' in event) {
      setEnrichmentEvents(prev => ({
        ...prev,
        [event.lead_id as string]: {
          event_type: event.event_type,
          lead_id: event.lead_id as string,
          status_message: 'status_message' in event ? event.status_message as string : undefined,
          agent_name: 'agent_name' in event ? event.agent_name as string : undefined,
        },
      }));
    }
  });

  useRealTimeEvent<LeadEnrichedEvent>('lead-enriched', (event) => {
    // The parent component will handle the update, so we just notify it.
    if (onLeadUpdate) {
      onLeadUpdate(event.lead);
    }
  });

  const allLeads = useMemo(() => {
    const combined = [...leads];
    return Array.from(new Map(combined.map(lead => [lead.id, lead])).values());
  }, [leads]);

  const { processingLeads, boardLeads } = useMemo(() => {
    const processing = allLeads.filter(lead => ['new', 'harvested', 'pending_enrichment', 'enriching'].includes(lead.status));
    const board = allLeads.filter(lead => lead.status === 'enriched');
    return { processingLeads: processing, boardLeads: board };
  }, [allLeads]);

  // Filter leads based on current filters
  const filteredLeads = useMemo(() => {
    return boardLeads.filter(lead => {
      const searchMatch = !filters.search ||
        lead.company_name.toLowerCase().includes(filters.search.toLowerCase()) ||
        (lead.website && lead.website.toLowerCase().includes(filters.search.toLowerCase()));
      
      const sectorMatch = filters.sector === 'all' || lead.company_sector === filters.sector;
      
      const qualificationMatch = filters.qualification === 'all' ||
        lead.qualification_tier === filters.qualification;
      
      const scoreMatch = filters.scoreRange === 'all' || (() => {
        const score = lead.relevance_score * 100;
        switch (filters.scoreRange) {
          case 'high': return score >= 80;
          case 'medium': return score >= 60 && score < 80;
          case 'low': return score < 60;
          default: return true;
        }
      })();
      
      return searchMatch && sectorMatch && qualificationMatch && scoreMatch;
    });
  }, [boardLeads, filters]);

  // Group leads by processing stage
  const leadsByStage = useMemo(() => {
    return filteredLeads.reduce((acc, lead) => {
      const stage = lead.processing_stage || 'lead_qualification';
      if (!acc[stage]) {
        acc[stage] = [];
      }
      acc[stage].push(lead);
      return acc;
    }, {} as Record<ProcessingStage, LeadData[]>);
  }, [filteredLeads]);

  const handleDragStart = (e: React.DragEvent, lead: LeadData) => {
    setDraggedLead(lead);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e: React.DragEvent, targetStage: ProcessingStage) => {
    e.preventDefault();
    if (draggedLead && draggedLead.processing_stage !== targetStage) {
      try {
        // Use the API hook to update the lead stage
        await updateLeadStageMutation.mutateAsync({
          id: draggedLead.id,
          stage: targetStage
        });
        
        // Call the optional callback
        const updatedLead = { ...draggedLead, processing_stage: targetStage };
        onLeadUpdate?.(updatedLead);
      } catch (error) {
        console.error('Failed to update lead stage:', error);
      }
    }
    setDraggedLead(null);
  };

  const resetFilters = () => {
    setFilters({ search: '', sector: 'all', qualification: 'all', scoreRange: 'all' });
  };

  const handleLeadExpand = (lead: LeadData) => {
    setSelectedLead(lead);
    setIsModalOpen(true);
  };

  const getStageStats = (stage: ProcessingStage) => {
    const stageLeads = leadsByStage[stage] || [];
    const totalValue = stageLeads.reduce((sum, lead) => sum + (lead.roi_potential_score * 100), 0);
    return {
      count: stageLeads.length,
      avgScore: stageLeads.length > 0 ? (totalValue / stageLeads.length).toFixed(1) : '0',
      highPotential: stageLeads.filter(lead => lead.qualification_tier === 'High Potential').length,
      avgRelevance: stageLeads.length > 0 ? 
        (stageLeads.reduce((sum, lead) => sum + (lead.relevance_score * 100), 0) / stageLeads.length).toFixed(1) : '0'
    };
  };

  const getStageIcon = (stage: ProcessingStage) => {
    switch (stage) {
      case 'lead_qualification':
        return <Target className="w-4 h-4" />;
      case 'analyzing_refining':
        return <RefreshCw className="w-4 h-4" />;
      case 'possibly_qualified':
        return <TrendingUp className="w-4 h-4" />;
      case 'prospecting':
        return <Search className="w-4 h-4" />;
      case 'revisando':
        return <RefreshCw className="w-4 h-4" />;
      case 'primeiras_mensagens':
        return <Users className="w-4 h-4" />;
      case 'negociando':
        return <TrendingUp className="w-4 h-4" />;
      case 'reuniao_agendada':
        return <Users className="w-4 h-4" />;
      default:
        return <Target className="w-4 h-4" />;
    }
  };

  const totalLeads = filteredLeads.length;
  const totalValue = filteredLeads.reduce((sum, lead) => sum + (lead.roi_potential_score * 100), 0);
  const avgValue = totalLeads > 0 ? (totalValue / totalLeads).toFixed(1) : '0';

  return (
    <div className="space-y-4">
      {/* Summary Header */}
      <Card className="bg-slate-900 border-slate-700">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
            <div className="space-y-2">
              <div className="text-2xl font-bold text-white">{totalLeads}</div>
              <div className="text-sm text-slate-400">{t('total_leads')}</div>
            </div>
            <div className="space-y-2">
              <div className="text-2xl font-bold text-green-400">{avgValue}%</div>
              <div className="text-sm text-slate-400">{t('avg_roi_potential')}</div>
            </div>
            <div className="space-y-2">
              <div className="text-2xl font-bold text-blue-400">
                {filteredLeads.filter(l => l.qualification_tier === 'High Potential').length}
              </div>
              <div className="text-sm text-slate-400">{t('high_potential')}</div>
            </div>
            <div className="space-y-2">
              <div className="text-2xl font-bold text-purple-400">
                {leadsByStage['reuniao_agendada']?.length || 0}
              </div>
              <div className="text-sm text-slate-400">{t('meetings_scheduled')}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filters Section */}
      <Card className="bg-slate-900 border-slate-700">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <Input
                placeholder={t('search_leads')}
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10 bg-slate-800 border-slate-600 text-white h-10"
              />
            </div>

            <Select value={filters.sector} onValueChange={(value) => setFilters(prev => ({ ...prev, sector: value }))}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white h-10">
                <SelectValue placeholder={t('all_sectors')} />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all">{t('all_sectors')}</SelectItem>
                {allLeads.map(lead => lead.company_sector).filter(Boolean).map(sector => (
                  <SelectItem key={sector} value={sector}>{sector}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.qualification} onValueChange={(value) => setFilters(prev => ({ ...prev, qualification: value }))}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white h-10">
                <SelectValue placeholder={t('all_levels')} />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all">{t('all_levels')}</SelectItem>
                {allLeads.map(lead => lead.qualification_tier).filter(Boolean).map(qual => (
                  <SelectItem key={qual} value={qual}>{qual.split(' ')[0]}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.scoreRange} onValueChange={(value) => setFilters(prev => ({ ...prev, scoreRange: value }))}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white h-10">
                <SelectValue placeholder={t('all_scores')} />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all">{t('all_scores')}</SelectItem>
                <SelectItem value="high">{t('high_score')}</SelectItem>
                <SelectItem value="medium">{t('medium_score')}</SelectItem>
                <SelectItem value="low">{t('low_score')}</SelectItem>
              </SelectContent>
            </Select>

            <Button 
              onClick={resetFilters}
              variant="outline"
              className="border-slate-600 text-slate-300 hover:bg-slate-700 h-10"
              size="sm"
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              {t('reset')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* CRM Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {/* Live Processing Column */}
        <div
          className="flex-shrink-0 w-80 bg-slate-900/50 rounded-lg border border-slate-700 border-l-4"
          style={{ borderLeftColor: '#38bdf8' }}
        >
          <div className="p-4 border-b border-slate-700">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <div style={{ color: '#38bdf8' }}>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                </div>
                <h3 className="font-medium text-white text-sm">{t('harvesting_enriching')}</h3>
              </div>
              <Badge variant="secondary" className="text-xs bg-slate-700 text-white">
                {processingLeads.length}
              </Badge>
            </div>
          </div>
          <div className="p-3 space-y-2 min-h-96 max-h-96 overflow-y-auto">
            {processingLeads.map(lead => (
              <CompactLeadCard
                key={lead.id}
                lead={lead}
                onExpand={handleLeadExpand}
                enrichmentEvent={enrichmentEvents[lead.id]}
              />
            ))}
            {processingLeads.length === 0 && (
              <div className="text-center text-slate-500 py-8">
                <div className="text-sm">{t('no_new_leads_processing')}</div>
              </div>
            )}
          </div>
        </div>

        {/* Existing Stage Columns */}
        {STAGE_CONFIGS.map(stage => {
          const stats = getStageStats(stage.id);
          
          return (
            <div
              key={stage.id}
              className={`flex-shrink-0 w-80 bg-slate-900/50 rounded-lg border border-slate-700 ${
                draggedLead ? 'hover:border-green-500/50' : ''
              }`}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, stage.id)}
              style={stage.style}
            >
              <div className="p-4 border-b border-slate-700">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div style={{ color: stage.color }}>
                      {getStageIcon(stage.id)}
                    </div>
                    <h3 className="font-medium text-white text-sm">{stage.label}</h3>
                  </div>
                  <Badge variant="secondary" className="text-xs bg-slate-700 text-white">
                    {stats.count}
                  </Badge>
                </div>
                <div className="text-xs text-slate-400 space-y-1">
                  <div>ROI: {stats.avgScore}% • Relevance: {stats.avgRelevance}%</div>
                  <div>High Potential: {stats.highPotential}</div>
                </div>
              </div>
              <div className="p-3 space-y-2 min-h-96 max-h-96 overflow-y-auto">
                {leadsByStage[stage.id]?.map(lead => (
                  <div
                    key={lead.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, lead)}
                    className={`cursor-move transition-opacity ${
                      draggedLead?.id === lead.id ? 'opacity-50' : 'hover:opacity-90'
                    }`}
                  >
                    <CompactLeadCard
                      lead={lead}
                      onExpand={handleLeadExpand}
                      isUpdated={recentlyUpdated[lead.id]}
                    />
                  </div>
                ))}
                {leadsByStage[stage.id]?.length === 0 && (
                  <div className="text-center text-slate-500 py-8">
                    <div className="text-sm">{t('no_leads_in_stage')}</div>
                    {draggedLead && (
                      <div className="text-xs mt-2 text-slate-400">{t('drop_lead_here')}</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Enhanced Summary Stats */}
      <Card className="bg-slate-900 border-slate-700">
        <CardContent className="p-4">
          <div className="grid grid-cols-3 md:grid-cols-9 gap-4 text-center">
            {STAGE_CONFIGS.map(stage => {
              const stats = getStageStats(stage.id);
              return (
                <div key={stage.id} className="space-y-2">
                  <div 
                    className="w-6 h-6 rounded-full mx-auto flex items-center justify-center text-white text-xs"
                    style={{ backgroundColor: stage.color }}
                  >
                    {stats.count}
                  </div>
                  <div className="text-xs font-medium text-white truncate">{stage.label}</div>
                  <div className="text-xs text-slate-400">
                    <div>ROI: {stats.avgScore}%</div>
                    <div>High: {stats.highPotential}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Loading Indicator */}
      {isLoading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 p-4 rounded-lg border border-slate-600">
            <div className="flex items-center space-x-2">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span className="text-white">{t('updating_lead_stage')}</span>
            </div>
          </div>
        </div>
      )}

      {/* Lead Details Modal */}
      <LeadDetailsModal 
        lead={selectedLead}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};
