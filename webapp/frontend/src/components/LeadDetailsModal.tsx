
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { LeadCard } from "./LeadCard";
import { LeadData } from "../types/nellia";

interface LeadDetailsModalProps {
  lead: LeadData | null;
  isOpen: boolean;
  onClose: () => void;
}

export const LeadDetailsModal = ({ lead, isOpen, onClose }: LeadDetailsModalProps) => {
  if (!lead) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md bg-slate-900 border-slate-700">
        <DialogHeader>
          <DialogTitle className="text-white">Lead Details</DialogTitle>
        </DialogHeader>
        <div className="mt-4">
          <LeadCard lead={lead} />
        </div>
      </DialogContent>
    </Dialog>
  );
};
