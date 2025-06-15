import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users } from "lucide-react";
import { useTranslation } from "../../hooks/useTranslation";

interface LeadsEmptyStateProps {
  onStartProspecting: () => void;
}

export const LeadsEmptyState = ({ onStartProspecting }: LeadsEmptyStateProps) => {
  const { t } = useTranslation();
  
  return (
    <Card className="text-center p-8 bg-slate-800 border-slate-700">
      <Users className="w-12 h-12 mx-auto mb-4 text-slate-500" />
      <h3 className="text-xl font-semibold text-white mb-2">{t('no_leads_found')}</h3>
      <p className="text-slate-400 mb-4">
        {t('start_prospecting_message')}
      </p>
      <Button onClick={onStartProspecting} className="bg-green-600 hover:bg-green-700 text-white">
        {t('start_prospecting')}
      </Button>
    </Card>
  );
};
