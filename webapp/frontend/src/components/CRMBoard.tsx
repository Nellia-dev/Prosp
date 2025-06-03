
import { useState, useMemo } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { CompactLeadCard } from './CompactLeadCard';
import { LeadDetailsModal } from './LeadDetailsModal';
import { LeadData } from '../types/nellia';
import { useTranslation } from '../hooks/useTranslation';
import { Search, RotateCcw } from 'lucide-react';

interface CRMBoardProps {
  leads: LeadData[];
  onLeadUpdate?: (lead: LeadData) => void;
}

const PROCESSING_STAGES = [
  { id: 'lead_qualification', label: 'lead_qualification', color: 'bg-blue-500' },
  { id: 'analyzing_refining', label: 'analyzing_refining', color: 'bg-yellow-500' },
  { id: 'possibly_qualified', label: 'possibly_qualified', color: 'bg-purple-500' },
  { id: 'prospecting', label: 'prospecting', color: 'bg-orange-500' },
  { id: 'revisando', label: 'revisando', color: 'bg-indigo-500' },
  { id: 'primeiras_mensagens', label: 'primeiras_mensagens', color: 'bg-green-500' },
  { id: 'negociando', label: 'negociando', color: 'bg-emerald-500' },
  { id: 'desqualificado', label: 'desqualificado', color: 'bg-red-500' },
  { id: 'reuniao_agendada', label: 'reuniao_agendada', color: 'bg-teal-500' }
];

export const CRMBoard = ({ leads, onLeadUpdate }: CRMBoardProps) => {
  const { t } = useTranslation();
  const [draggedLead, setDraggedLead] = useState<LeadData | null>(null);
  const [selectedLead, setSelectedLead] = useState<LeadData | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [filters, setFilters] = useState({
    search: '',
    sector: 'all',
    qualification: 'all',
    scoreRange: 'all'
  });

  // Filter leads based on current filters
  const filteredLeads = useMemo(() => {
    return leads.filter(lead => {
      const searchMatch = !filters.search || 
        lead.company_name.toLowerCase().includes(filters.search.toLowerCase()) ||
        lead.website.toLowerCase().includes(filters.search.toLowerCase());
      
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
  }, [leads, filters]);

  // Group leads by processing stage
  const leadsByStage = useMemo(() => {
    const grouped: Record<string, LeadData[]> = {};
    PROCESSING_STAGES.forEach(stage => {
      grouped[stage.id] = filteredLeads.filter(lead => lead.processing_stage === stage.id);
    });
    return grouped;
  }, [filteredLeads]);

  // Get unique sectors and qualifications for filter options
  const sectors = [...new Set(leads.map(lead => lead.company_sector))];
  const qualifications = [...new Set(leads.map(lead => lead.qualification_tier))];

  const handleDragStart = (e: React.DragEvent, lead: LeadData) => {
    setDraggedLead(lead);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, targetStage: string) => {
    e.preventDefault();
    if (draggedLead && draggedLead.processing_stage !== targetStage) {
      const updatedLead = { ...draggedLead, processing_stage: targetStage as LeadData['processing_stage'] };
      onLeadUpdate?.(updatedLead);
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

  const getStageStats = (stageId: string) => {
    const stageLeads = leadsByStage[stageId] || [];
    const totalValue = stageLeads.reduce((sum, lead) => sum + (lead.roi_potential_score * 100), 0);
    return {
      count: stageLeads.length,
      avgScore: stageLeads.length > 0 ? (totalValue / stageLeads.length).toFixed(1) : '0',
      highPotential: stageLeads.filter(lead => lead.qualification_tier === 'High Potential').length
    };
  };

  return (
    <div className="space-y-4">
      {/* Filters Section */}
      <Card className="bg-slate-900 border-slate-700">
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <Input
                placeholder="Buscar leads..."
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10 bg-slate-800 border-slate-600 text-white h-10"
              />
            </div>

            <Select value={filters.sector} onValueChange={(value) => setFilters(prev => ({ ...prev, sector: value }))}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white h-10">
                <SelectValue placeholder="All Sectors" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all">All Sectors</SelectItem>
                {sectors.map(sector => (
                  <SelectItem key={sector} value={sector}>{sector}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.qualification} onValueChange={(value) => setFilters(prev => ({ ...prev, qualification: value }))}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white h-10">
                <SelectValue placeholder="All Levels" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all">All Levels</SelectItem>
                {qualifications.map(qual => (
                  <SelectItem key={qual} value={qual}>{qual.split(' ')[0]}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filters.scoreRange} onValueChange={(value) => setFilters(prev => ({ ...prev, scoreRange: value }))}>
              <SelectTrigger className="bg-slate-800 border-slate-600 text-white h-10">
                <SelectValue placeholder="All Scores" />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="all">All Scores</SelectItem>
                <SelectItem value="high">High (80%+)</SelectItem>
                <SelectItem value="medium">Medium (60-79%)</SelectItem>
                <SelectItem value="low">Low (&lt;60%)</SelectItem>
              </SelectContent>
            </Select>

            <Button 
              onClick={resetFilters}
              variant="outline"
              className="border-slate-600 text-slate-300 hover:bg-slate-700 h-10"
              size="sm"
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* CRM Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {PROCESSING_STAGES.map(stage => {
          const stats = getStageStats(stage.id);
          
          return (
            <div
              key={stage.id}
              className="flex-shrink-0 w-80 bg-slate-900/50 rounded-lg border border-slate-700"
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, stage.id)}
            >
              {/* Stage Header */}
              <div className="p-4 border-b border-slate-700">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div className={`w-3 h-3 rounded-full ${stage.color}`}></div>
                    <h3 className="font-medium text-white text-sm">{t(stage.label)}</h3>
                  </div>
                  <Badge variant="secondary" className="text-xs bg-slate-700 text-white">
                    {stats.count}
                  </Badge>
                </div>
                <div className="text-xs text-slate-400 space-y-1">
                  <div>Avg: {stats.avgScore}% • High: {stats.highPotential}</div>
                </div>
              </div>

              {/* Stage Content */}
              <div className="p-3 space-y-2 min-h-96 max-h-96 overflow-y-auto">
                {leadsByStage[stage.id]?.map(lead => (
                  <div
                    key={lead.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, lead)}
                    className="cursor-move"
                  >
                    <CompactLeadCard 
                      lead={lead} 
                      onExpand={handleLeadExpand}
                    />
                  </div>
                ))}
                
                {leadsByStage[stage.id]?.length === 0 && (
                  <div className="text-center text-slate-500 py-8">
                    <div className="text-sm">No leads</div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Stats */}
      <Card className="bg-slate-900 border-slate-700">
        <CardContent className="p-4">
          <div className="grid grid-cols-3 md:grid-cols-9 gap-4 text-center">
            {PROCESSING_STAGES.map(stage => {
              const stats = getStageStats(stage.id);
              return (
                <div key={stage.id} className="space-y-2">
                  <div className={`w-4 h-4 rounded-full ${stage.color} mx-auto`}></div>
                  <div className="text-xs font-medium text-white">{t(stage.label)}</div>
                  <div className="text-xl font-bold text-white">{stats.count}</div>
                  <div className="text-xs text-slate-400">{stats.avgScore}%</div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Lead Details Modal */}
      <LeadDetailsModal 
        lead={selectedLead}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
};
