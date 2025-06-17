import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUpdateLead, useDeleteLead, useProcessLead } from '../hooks/api/useUnifiedApi';
import { LeadData, ProcessingStage, QualificationTier, PROCESSING_STAGES, QUALIFICATION_TIERS } from '../types/unified';
import { useTranslation } from '../hooks/useTranslation';
import {
  Save,
  Trash2,
  Play,
  Edit3,
  Eye,
  ExternalLink,
  Building,
  Globe,
  Target,
  TrendingUp,
  Users,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { useToast } from '../hooks/use-toast';

interface LeadDetailsModalProps {
  lead: LeadData | null;
  isOpen: boolean;
  onClose: () => void;
  onLeadUpdate?: (lead: LeadData) => void;
}


export const LeadDetailsModal = ({ lead, isOpen, onClose, onLeadUpdate }: LeadDetailsModalProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<LeadData>>({});

  const updateLeadMutation = useUpdateLead();
  const deleteLeadMutation = useDeleteLead();
  const processLeadMutation = useProcessLead();

  useEffect(() => {
    if (lead) {
      setFormData({
        company_name: lead.company_name,
        website: lead.website,
        company_sector: lead.company_sector,
        qualification_tier: lead.qualification_tier,
        processing_stage: lead.processing_stage,
        pain_point_analysis: lead.pain_point_analysis,
        purchase_triggers: lead.purchase_triggers,
        relevance_score: lead.relevance_score,
        roi_potential_score: lead.roi_potential_score,
      });
    }
  }, [lead]);

  if (!lead) return null;

  const handleInputChange = (field: string, value: string | number | string[]) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    try {
      // Now using the proper snake_case format that matches backend
      const updateData = {
        company_name: formData.company_name,
        website: formData.website,
        company_sector: formData.company_sector,
        qualification_tier: formData.qualification_tier,
        relevance_score: formData.relevance_score,
        roi_potential_score: formData.roi_potential_score,
        processing_stage: formData.processing_stage,
        pain_point_analysis: formData.pain_point_analysis,
        purchase_triggers: formData.purchase_triggers,
      };

      const updatedLead = await updateLeadMutation.mutateAsync({
        id: lead.id,
        data: updateData
      });

      // API response is now already in the correct format (LeadData)
      onLeadUpdate?.(updatedLead);
      setIsEditing(false);
      toast({
        title: t('lead_updated'),
        description: t('lead_updated_success'),
      });
    } catch (error) {
      toast({
        title: t('error'),
        description: t('update_error'),
        variant: "destructive",
      });
    }
  };

  const handleDelete = async () => {
    if (confirm(t('delete_confirmation'))) {
      try {
        await deleteLeadMutation.mutateAsync(lead.id);
        toast({
          title: t('lead_deleted'),
          description: t('lead_deleted_success'),
        });
        onClose();
      } catch (error) {
        toast({
          title: t('error'),
          description: t('delete_error'),
          variant: "destructive",
        });
      }
    }
  };

  const handleProcess = async () => {
    try {
      await processLeadMutation.mutateAsync(lead.id);
      toast({
        title: t('processing_started'),
        description: t('processing_started_success'),
      });
    } catch (error) {
      toast({
        title: t('error'),
        description: t('process_error'),
        variant: "destructive",
      });
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    if (score >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const getQualificationColor = (tier: string) => {
    switch (tier) {
      case 'High Potential': return 'bg-green-500';
      case 'Medium Potential': return 'bg-yellow-500';
      case 'Low Potential': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-slate-900 border-slate-700">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="text-white flex items-center space-x-2">
              <Building className="w-5 h-5" />
              <span>{isEditing ? formData.company_name : lead.company_name}</span>
            </DialogTitle>
            <div className="flex items-center space-x-2">
              <Badge className={`${getQualificationColor(lead.qualification_tier)} text-white`}>
                {lead.qualification_tier}
              </Badge>
              <Badge variant="outline" className="text-slate-300">
                {t(lead.processing_stage)}
              </Badge>
            </div>
          </div>
        </DialogHeader>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-5 bg-slate-800">
            <TabsTrigger value="overview" className="text-slate-300">{t('overview')}</TabsTrigger>
            <TabsTrigger value="details" className="text-slate-300">{t('details')}</TabsTrigger>
            <TabsTrigger value="insights" className="text-slate-300">{t('insights')}</TabsTrigger>
            <TabsTrigger value="strategy" className="text-slate-300">{t('strategy')}</TabsTrigger>
            <TabsTrigger value="actions" className="text-slate-300">{t('actions')}</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Basic Information */}
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white text-sm flex items-center">
                    <Building className="w-4 h-4 mr-2" />
                    {t('company_information')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {isEditing ? (
                    <>
                      <div>
                        <Label className="text-slate-300">{t('company_name')}</Label>
                        <Input
                          value={formData.company_name || ''}
                          onChange={(e) => handleInputChange('company_name', e.target.value)}
                          className="bg-slate-700 border-slate-600 text-white"
                        />
                      </div>
                      <div>
                        <Label className="text-slate-300">{t('website')}</Label>
                        <Input
                          value={formData.website || ''}
                          onChange={(e) => handleInputChange('website', e.target.value)}
                          className="bg-slate-700 border-slate-600 text-white"
                        />
                      </div>
                      <div>
                        <Label className="text-slate-300">{t('sector')}</Label>
                        <Input
                          value={formData.company_sector || ''}
                          onChange={(e) => handleInputChange('company_sector', e.target.value)}
                          className="bg-slate-700 border-slate-600 text-white"
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex items-center space-x-2">
                        <Globe className="w-4 h-4 text-slate-400" />
                        <a
                          href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 flex items-center"
                        >
                          {lead.website}
                          <ExternalLink className="w-3 h-3 ml-1" />
                        </a>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Target className="w-4 h-4 text-slate-400" />
                        <span className="text-slate-300">{lead.company_sector}</span>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>

              {/* Scores */}
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white text-sm flex items-center">
                    <TrendingUp className="w-4 h-4 mr-2" />
                    {t('performance_scores')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {isEditing ? (
                    <>
                      <div>
                        <Label className="text-slate-300">{t('relevance_score')}</Label>
                        <Input
                          type="number"
                          min="0"
                          max="1"
                          step="0.01"
                          value={formData.relevance_score || 0}
                          onChange={(e) => handleInputChange('relevance_score', parseFloat(e.target.value))}
                          className="bg-slate-700 border-slate-600 text-white"
                        />
                      </div>
                      <div>
                        <Label className="text-slate-300">{t('roi_potential')}</Label>
                        <Input
                          type="number"
                          min="0"
                          max="1"
                          step="0.01"
                          value={formData.roi_potential_score || 0}
                          onChange={(e) => handleInputChange('roi_potential_score', parseFloat(e.target.value))}
                          className="bg-slate-700 border-slate-600 text-white"
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-300">{t('relevance')}</span>
                        <span className={`font-bold ${getScoreColor(lead.relevance_score)}`}>
                          {(lead.relevance_score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-300">{t('roi_potential')}</span>
                        <span className={`font-bold ${getScoreColor(lead.roi_potential_score)}`}>
                          {(lead.roi_potential_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="details" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Qualification & Stage */}
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white text-sm">Classification</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {isEditing ? (
                    <>
                      <div>
                        <Label className="text-slate-300">Qualification Tier</Label>
                        <Select
                          value={formData.qualification_tier}
                          onValueChange={(value) => handleInputChange('qualification_tier', value)}
                        >
                          <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-slate-700 border-slate-600">
                            {QUALIFICATION_TIERS.map(tier => (
                              <SelectItem key={tier} value={tier}>{tier}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-slate-300">Processing Stage</Label>
                        <Select
                          value={formData.processing_stage}
                          onValueChange={(value) => handleInputChange('processing_stage', value)}
                        >
                          <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-slate-700 border-slate-600">
                            {PROCESSING_STAGES.map(stage => (
                              <SelectItem key={stage} value={stage}>{t(stage)}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-300">Qualification</span>
                        <Badge className={`${getQualificationColor(lead.qualification_tier)} text-white`}>
                          {lead.qualification_tier}
                        </Badge>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-300">Stage</span>
                        <Badge variant="outline" className="text-slate-300">
                          {t(lead.processing_stage)}
                        </Badge>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>

              {/* Contact Information */}
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white text-sm flex items-center">
                    <Users className="w-4 h-4 mr-2" />
                    Contact Insights
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-300">Likely Role</span>
                    <span className="text-white">{lead.persona?.likely_role || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-300">Decision Maker</span>
                    <span className="text-white">
                      {lead.persona?.decision_maker_probability
                        ? `${(lead.persona.decision_maker_probability * 100).toFixed(0)}%`
                        : 'Unknown'
                      }
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="insights" className="space-y-4">
            {/* Pain Points */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-sm flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  Pain Points
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isEditing ? (
                  <Textarea
                    value={formData.pain_point_analysis?.join('\n') || ''}
                    onChange={(e) => handleInputChange('pain_point_analysis', e.target.value.split('\n').filter(p => p.trim()))}
                    placeholder="Enter pain points (one per line)"
                    className="bg-slate-700 border-slate-600 text-white min-h-24"
                  />
                ) : (
                  <div className="space-y-2">
                    {lead.pain_point_analysis && lead.pain_point_analysis.length > 0 ? (
                      lead.pain_point_analysis.map((point, index) => (
                        <div key={index} className="flex items-start space-x-2">
                          <AlertTriangle className="w-3 h-3 text-orange-400 mt-1 flex-shrink-0" />
                          <span className="text-slate-300">{point}</span>
                        </div>
                      ))
                    ) : (
                      <span className="text-slate-500">No pain points identified</span>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Triggers */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-sm flex items-center">
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Buying Triggers
                </CardTitle>
              </CardHeader>
              <CardContent>
                {isEditing ? (
                  <Textarea
                    value={formData.purchase_triggers?.join('\n') || ''}
                    onChange={(e) => handleInputChange('purchase_triggers', e.target.value.split('\n').filter(t => t.trim()))}
                    placeholder="Enter buying triggers (one per line)"
                    className="bg-slate-700 border-slate-600 text-white min-h-24"
                  />
                ) : (
                  <div className="space-y-2">
                    {lead.purchase_triggers && lead.purchase_triggers.length > 0 ? (
                      lead.purchase_triggers.map((trigger, index) => (
                        <div key={index} className="flex items-start space-x-2">
                          <CheckCircle className="w-3 h-3 text-green-400 mt-1 flex-shrink-0" />
                          <span className="text-slate-300">{trigger}</span>
                        </div>
                      ))
                    ) : (
                      <span className="text-slate-500">No triggers identified</span>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="strategy" className="space-y-4">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-sm flex items-center">
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Approach Plan
                </CardTitle>
              </CardHeader>
              <CardContent>
                {lead.enrichment_data?.enhanced_strategy?.detailed_approach_plan ? (
                  <div className="space-y-4 text-slate-300">
                    <div>
                      <h4 className="font-semibold text-white">Main Objective</h4>
                      <p>{lead.enrichment_data.enhanced_strategy.detailed_approach_plan.main_objective}</p>
                    </div>
                    <div>
                      <h4 className="font-semibold text-white">Elevator Pitch</h4>
                      <p>{lead.enrichment_data.enhanced_strategy.detailed_approach_plan.adapted_elevator_pitch}</p>
                    </div>
                    <div>
                      <h4 className="font-semibold text-white">Contact Sequence</h4>
                      <div className="space-y-2">
                        {lead.enrichment_data.enhanced_strategy.detailed_approach_plan.contact_sequence.map((step: any) => (
                          <div key={step.step_number} className="p-2 bg-slate-850 rounded-md">
                            <p className="font-bold">{step.step_number}. {step.channel}</p>
                            <p><span className="font-semibold">Objective:</span> {step.objective}</p>
                            <p><span className="font-semibold">CTA:</span> {step.cta}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-slate-500">No detailed approach plan available. Enrich the lead to generate one.</p>
                )}
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white text-sm flex items-center">
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Personalized Message
                </CardTitle>
              </CardHeader>
              <CardContent>
                {lead.enrichment_data?.enhanced_personalized_message?.primary_message ? (
                  <div className="space-y-2 text-slate-300 bg-slate-850 p-3 rounded-md">
                    <p className="font-semibold text-white">{lead.enrichment_data.enhanced_personalized_message.primary_message.subject_line}</p>
                    <p className="whitespace-pre-wrap">{lead.enrichment_data.enhanced_personalized_message.primary_message.message_body}</p>
                  </div>
                ) : (
                  <p className="text-slate-500">No personalized message available.</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="actions" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white text-sm">Lead Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button
                    onClick={handleProcess}
                    disabled={processLeadMutation.isPending}
                    className="w-full bg-blue-600 hover:bg-blue-700"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    {processLeadMutation.isPending ? 'Processing...' : 'Process Lead'}
                  </Button>

                  <Button
                    onClick={() => setIsEditing(!isEditing)}
                    variant="outline"
                    className="w-full border-slate-600 text-slate-300 hover:bg-slate-700"
                  >
                    {isEditing ? (
                      <>
                        <Eye className="w-4 h-4 mr-2" />
                        View Mode
                      </>
                    ) : (
                      <>
                        <Edit3 className="w-4 h-4 mr-2" />
                        Edit Mode
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>

              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white text-sm">Metadata</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Created</span>
                    <span className="text-slate-300">
                      {new Date(lead.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Updated</span>
                    <span className="text-slate-300">
                      {new Date(lead.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Lead ID</span>
                    <span className="text-slate-300 font-mono text-xs">{lead.id}</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Action Buttons */}
        <div className="flex justify-between items-center pt-4 border-t border-slate-700">
          <Button
            onClick={handleDelete}
            disabled={deleteLeadMutation.isPending}
            variant="destructive"
            size="sm"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            {deleteLeadMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>

          <div className="flex space-x-2">
            <Button onClick={onClose} variant="outline" size="sm">
              Cancel
            </Button>
            {isEditing && (
              <Button
                onClick={handleSave}
                disabled={updateLeadMutation.isPending}
                size="sm"
              >
                <Save className="w-4 h-4 mr-2" />
                {updateLeadMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
