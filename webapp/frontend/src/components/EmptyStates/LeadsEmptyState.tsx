import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users } from "lucide-react";

interface LeadsEmptyStateProps {
  onStartProspecting: () => void;
}

export const LeadsEmptyState = ({ onStartProspecting }: LeadsEmptyStateProps) => (
  <Card className="text-center p-8 bg-slate-800 border-slate-700">
    <Users className="w-12 h-12 mx-auto mb-4 text-slate-500" />
    <h3 className="text-xl font-semibold text-white mb-2">No Leads Found</h3>
    <p className="text-slate-400 mb-4">
      Start the prospecting process to find your first leads.
    </p>
    <Button onClick={onStartProspecting} className="bg-green-600 hover:bg-green-700 text-white">
      Start Prospecting
    </Button>
  </Card>
);
