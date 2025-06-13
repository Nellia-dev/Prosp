
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Building2, Globe, Target, TrendingUp } from "lucide-react";
import { LeadData } from "../types/nellia";
import { useTranslation } from "../hooks/useTranslation";

interface LeadCardProps {
  lead: LeadData;
  onClick?: () => void;
}

export const LeadCard = ({ lead, onClick }: LeadCardProps) => {
  const { t } = useTranslation();

  const getQualificationColor = (tier: string) => {
    switch (tier) {
      case 'High Potential': return 'bg-green-500';
      case 'Medium Potential': return 'bg-yellow-500';
      case 'Low Potential': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStageProgress = (stage: string) => {
    const stages = ['intake', 'analysis', 'persona', 'strategy', 'message', 'completed'];
    return ((stages.indexOf(stage) + 1) / stages.length) * 100;
  };

  const formatScore = (score: number) => (score * 100).toFixed(0);

  return (
    <Card 
      className="relative overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700 hover:border-green-500/50 transition-all duration-300 cursor-pointer group"
      onClick={onClick}
    >
      <div className={`absolute top-0 left-0 w-full h-1 ${getQualificationColor(lead.qualification_tier)}`} />
      
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-white text-base font-semibold truncate">
              {lead.company_name}
            </CardTitle>
            <div className="flex items-center text-slate-400 text-sm mt-1">
              <Globe className="w-3 h-3 mr-1" />
              <span className="truncate">{lead.website}</span>
            </div>
          </div>
          <Badge variant="outline" className="ml-2 text-xs shrink-0">
            {lead.qualification_tier}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center space-y-1">
            <div className="flex items-center justify-center text-slate-400 text-xs">
              <Target className="w-3 h-3 mr-1" />
              {t('relevance_score')}
            </div>
            <div className="text-white text-lg font-bold">
              {formatScore(lead.relevance_score)}%
            </div>
          </div>

          <div className="text-center space-y-1">
            <div className="flex items-center justify-center text-slate-400 text-xs">
              <TrendingUp className="w-3 h-3 mr-1" />
              {t('roi_potential')}
            </div>
            <div className="text-white text-lg font-bold">
              {formatScore(lead.roi_potential_score)}%
            </div>
          </div>

          <div className="text-center space-y-1">
            <div className="flex items-center justify-center text-slate-400 text-xs">
              <Building2 className="w-3 h-3 mr-1" />
              {t('brazilian_market_fit')}
            </div>
            <div className="text-white text-lg font-bold">
              {formatScore(lead.brazilian_market_fit)}%
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">{t('processing_progress')}</span>
            <span className="text-white capitalize">{lead.processing_stage}</span>
          </div>
          <Progress 
            value={getStageProgress(lead.processing_stage)} 
            className="h-2"
          />
        </div>

        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400">{lead.company_sector}</span>
          <span className="text-slate-400">
            {new Date(lead.updated_at).toLocaleDateString()}
          </span>
        </div>

        {lead.persona && (
          <div className="border-t border-slate-700 pt-3">
            <div className="text-xs text-slate-400 mb-1">{t('likely_contact')}</div>
            <div className="text-sm text-white">{lead.persona.likely_role}</div>
            <div className="text-xs text-green-400">
              {(lead.persona.decision_maker_probability * 100).toFixed(0)}% {t('decision_maker_probability')}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
