import { Card } from "@/components/ui/card";
import { Bot } from "lucide-react";

export const AgentsEmptyState = () => (
  <Card className="text-center p-8 bg-slate-800 border-slate-700">
    <Bot className="w-12 h-12 mx-auto mb-4 text-slate-500" />
    <h3 className="text-xl font-semibold text-white mb-2">No Agents Configured</h3>
    <p className="text-slate-400">
      Agents will be automatically configured when you set up your business context.
    </p>
    {/* Optionally, add a button to guide the user to business context setup */}
    {/* <Button onClick={() => navigate('/context')} className="mt-4">Set Up Business Context</Button> */}
  </Card>
);
