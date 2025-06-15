import { Card } from "@/components/ui/card";
import { Bot } from "lucide-react";
import { useTranslation } from "../../hooks/useTranslation";

export const AgentsEmptyState = () => {
  const { t } = useTranslation();
  
  return (
    <Card className="text-center p-8 bg-slate-800 border-slate-700">
      <Bot className="w-12 h-12 mx-auto mb-4 text-slate-500" />
      <h3 className="text-xl font-semibold text-white mb-2">{t('no_agents_configured')}</h3>
      <p className="text-slate-400">
        {t('agents_auto_configured')}
      </p>
      {/* Optionally, add a button to guide the user to business context setup */}
      {/* <Button onClick={() => navigate('/context')} className="mt-4">Set Up Business Context</Button> */}
    </Card>
  );
};
