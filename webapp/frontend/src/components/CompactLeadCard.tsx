
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Globe, Eye } from "lucide-react";
import { LeadData } from "../types/unified";
import { useState } from "react";

interface EnrichmentEvent {
  status_message?: string;
  agent_name?: string;
}

interface CompactLeadCardProps {
  lead: LeadData;
  onExpand?: (lead: LeadData) => void;
  isUpdated?: boolean;
  enrichmentEvent?: EnrichmentEvent;
}

export const CompactLeadCard = ({ lead, onExpand, isUpdated, enrichmentEvent }: CompactLeadCardProps) => {
  const [isHovered, setIsHovered] = useState(false);

  const getQualificationColor = (tier: string) => {
    switch (tier) {
      case 'High Potential': return 'bg-green-500';
      case 'Medium Potential': return 'bg-yellow-500';
      case 'Low Potential': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const formatScore = (score: number) => (score * 100).toFixed(0);

  return (
    <Card
      className={`relative overflow-hidden bg-slate-800 border-slate-600 hover:border-green-500/50 transition-all duration-200 cursor-pointer group mb-2 ${isUpdated ? 'glow-animation' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onExpand?.(lead)}
    >
      <div className={`absolute top-0 left-0 w-full h-1 ${getQualificationColor(lead.qualification_tier)}`} />
      
      <CardContent className="p-3 space-y-2">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h4 className="text-white text-sm font-medium truncate">
              {lead.company_name}
            </h4>
            <div className="flex items-center text-slate-400 text-xs mt-1">
              <Globe className="w-3 h-3 mr-1" />
              <span className="truncate">{lead.website.replace('https://', '').replace('http://', '')}</span>
            </div>
          </div>
          {isHovered && (
            <Eye className="w-4 h-4 text-slate-400 ml-2 shrink-0" />
          )}
        </div>

        {/* Enrichment Status or Scores */}
        {enrichmentEvent ? (
          <div className="text-center text-xs text-slate-300 py-2">
            <p className="font-semibold">{enrichmentEvent.status_message || 'Processing...'}</p>
            {enrichmentEvent.agent_name && <p className="text-slate-500">Agent: {enrichmentEvent.agent_name}</p>}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div>
                <div className="text-slate-400">REL</div>
                <div className="text-white font-semibold">{formatScore(lead.relevance_score)}%</div>
              </div>
              <div>
                <div className="text-slate-400">ROI</div>
                <div className="text-white font-semibold">{formatScore(lead.roi_potential_score)}%</div>
              </div>
              <div>
                <div className="text-slate-400">FIT</div>
                <div className="text-white font-semibold">{formatScore(lead.brazilian_market_fit)}%</div>
              </div>
            </div>
            <div className="flex items-center justify-between mt-2">
              <Badge variant="outline" className="text-xs text-slate-300 border-slate-600 px-1 py-0">
                {lead.qualification_tier.split(' ')[0]}
              </Badge>
              <span className="text-xs text-slate-400 truncate ml-2">{lead.company_sector}</span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};
