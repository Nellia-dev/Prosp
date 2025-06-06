import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Save, Plus, X, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { BusinessContext } from "../types/unified";
import { BusinessContextResponse, BusinessContextRequest } from "../types/api";
import { useTranslation } from "../hooks/useTranslation";
import { useBusinessContext, useUpdateBusinessContext } from "../hooks/api/useUnifiedApi";

export const BusinessContextCenter = () => {
  const { t } = useTranslation();
  const { data: existingContext, isLoading } = useBusinessContext();
  const updateContextMutation = useUpdateBusinessContext();

  const [context, setContext] = useState<BusinessContext>({
    business_description: '',
    product_service_description: '',
    target_market: '',
    value_proposition: '',
    ideal_customer: '',
    pain_points: [],
    competitive_advantage: '',
    competitors: [],
    industry_focus: [],
    geographic_focus: [],
  });

  const [newPainPoint, setNewPainPoint] = useState('');
  const [newIndustry, setNewIndustry] = useState('');
  const [hasChanges, setHasChanges] = useState(false);

  // Adapter functions to convert between API and unified types
  const adaptApiToUnified = (apiContext: BusinessContextResponse): BusinessContext => ({
    id: apiContext.id,
    business_description: apiContext.business_description,
    product_service_description: apiContext.product_service_description,
    target_market: apiContext.target_market,
    value_proposition: apiContext.value_proposition,
    ideal_customer: apiContext.ideal_customer,
    pain_points: apiContext.pain_points,
    competitive_advantage: apiContext.competitive_advantage,
    competitors: apiContext.competitors,
    industry_focus: apiContext.industry_focus,
    geographic_focus: apiContext.geographic_focus,
    is_active: apiContext.is_active,
    created_at: apiContext.created_at,
    updated_at: apiContext.updated_at
  });

  const adaptUnifiedToApi = (unifiedContext: BusinessContext): BusinessContextRequest => ({
    business_description: unifiedContext.business_description,
    product_service_description: unifiedContext.product_service_description,
    target_market: unifiedContext.target_market,
    value_proposition: unifiedContext.value_proposition,
    ideal_customer: unifiedContext.ideal_customer || '',
    pain_points: unifiedContext.pain_points,
    competitive_advantage: unifiedContext.competitive_advantage,
    competitors: unifiedContext.competitors,
    industry_focus: unifiedContext.industry_focus,
    geographic_focus: unifiedContext.geographic_focus,
  });

  // Load existing context when data is available
  useEffect(() => {
    if (existingContext) {
      const adaptedContext = adaptApiToUnified(existingContext);
      setContext(adaptedContext);
      setHasChanges(false);
    }
  }, [existingContext]);

  // Track changes
  useEffect(() => {
    if (existingContext) {
      const adaptedExisting = adaptApiToUnified(existingContext);
      const hasChanged = JSON.stringify(context) !== JSON.stringify(adaptedExisting);
      setHasChanges(hasChanged);
    }
  }, [context, existingContext]);

  const addPainPoint = () => {
    if (newPainPoint.trim()) {
      setContext(prev => ({
        ...prev,
        pain_points: [...prev.pain_points, newPainPoint.trim()]
      }));
      setNewPainPoint('');
    }
  };

  const removePainPoint = (index: number) => {
    setContext(prev => ({
      ...prev,
      pain_points: prev.pain_points.filter((_, i) => i !== index)
    }));
  };

  const addIndustry = () => {
    if (newIndustry.trim()) {
      setContext(prev => ({
        ...prev,
        industry_focus: [...prev.industry_focus, newIndustry.trim()]
      }));
      setNewIndustry('');
    }
  };

  const removeIndustry = (index: number) => {
    setContext(prev => ({
      ...prev,
      industry_focus: prev.industry_focus.filter((_, i) => i !== index)
    }));
  };

  const handleSave = async () => {
    try {
      const updateData = adaptUnifiedToApi(context);
      await updateContextMutation.mutateAsync(updateData);
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save business context:', error);
    }
  };

  const resetChanges = () => {
    if (existingContext) {
      const adaptedContext = adaptApiToUnified(existingContext);
      setContext(adaptedContext);
      setHasChanges(false);
    }
  };

  if (isLoading) {
    return (
      <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
        <CardContent className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-green-500" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-white text-lg">{t('business_context')}</CardTitle>
          <div className="flex items-center space-x-2">
            {hasChanges && (
              <Button 
                onClick={resetChanges} 
                size="sm" 
                variant="outline"
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                Reset
              </Button>
            )}
            <Button 
              onClick={handleSave} 
              size="sm" 
              className="bg-green-600 hover:bg-green-700"
              disabled={!hasChanges || updateContextMutation.isPending}
            >
              {updateContextMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Save Context
            </Button>
          </div>
        </div>
        <p className="text-slate-400 text-sm">
          Configure your business context to optimize lead processing and agent behavior
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Success/Error Messages */}
        {updateContextMutation.isSuccess && (
          <Alert className="bg-green-900/20 border-green-700">
            <CheckCircle className="h-4 w-4" />
            <AlertDescription className="text-green-300">
              Business context updated successfully!
            </AlertDescription>
          </Alert>
        )}

        {updateContextMutation.isError && (
          <Alert className="bg-red-900/20 border-red-700">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-red-300">
              Failed to update business context. Please try again.
            </AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-white text-sm font-medium">Business Description</label>
            <Textarea
              value={context.business_description}
              onChange={(e) => setContext(prev => ({ ...prev, business_description: e.target.value }))}
              placeholder="Describe your business..."
              className="bg-slate-800 border-slate-600 text-white min-h-[100px]"
            />
          </div>

          <div className="space-y-2">
            <label className="text-white text-sm font-medium">Product/Service Description</label>
            <Textarea
              value={context.product_service_description}
              onChange={(e) => setContext(prev => ({ ...prev, product_service_description: e.target.value }))}
              placeholder="Describe your products and services..."
              className="bg-slate-800 border-slate-600 text-white min-h-[100px]"
            />
          </div>

          <div className="space-y-2">
            <label className="text-white text-sm font-medium">Target Market</label>
            <Textarea
              value={context.target_market}
              onChange={(e) => setContext(prev => ({ ...prev, target_market: e.target.value }))}
              placeholder="Define your target market..."
              className="bg-slate-800 border-slate-600 text-white min-h-[100px]"
            />
          </div>

          <div className="space-y-2">
            <label className="text-white text-sm font-medium">Value Proposition</label>
            <Textarea
              value={context.value_proposition}
              onChange={(e) => setContext(prev => ({ ...prev, value_proposition: e.target.value }))}
              placeholder="What is your unique value proposition?"
              className="bg-slate-800 border-slate-600 text-white"
            />
          </div>

          <div className="space-y-2">
            <label className="text-white text-sm font-medium">Ideal Customer</label>
            <Textarea
              value={context.ideal_customer || ''}
              onChange={(e) => setContext(prev => ({ ...prev, ideal_customer: e.target.value }))}
              placeholder="Describe your ideal customer..."
              className="bg-slate-800 border-slate-600 text-white"
            />
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-white text-sm font-medium mb-2 block">Pain Points You Solve</label>
            <div className="flex space-x-2 mb-3">
              <Input
                value={newPainPoint}
                onChange={(e) => setNewPainPoint(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addPainPoint()}
                placeholder="Add a pain point that you solve..."
                className="bg-slate-800 border-slate-600 text-white"
              />
              <Button onClick={addPainPoint} size="sm" variant="outline">
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {context.pain_points.map((point, index) => (
                <Badge key={index} variant="secondary" className="bg-slate-700 text-white">
                  {point}
                  <Button
                    onClick={() => removePainPoint(index)}
                    variant="ghost"
                    size="sm"
                    className="ml-2 h-4 w-4 p-0 hover:bg-slate-600"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
            {context.pain_points.length === 0 && (
              <p className="text-slate-500 text-sm mt-2">
                Add pain points to help agents understand what problems you solve
              </p>
            )}
          </div>

          <div>
            <label className="text-white text-sm font-medium mb-2 block">Industry Focus</label>
            <div className="flex space-x-2 mb-3">
              <Input
                value={newIndustry}
                onChange={(e) => setNewIndustry(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addIndustry()}
                placeholder="Add industry sector (e.g., E-commerce, SaaS, Fintech...)"
                className="bg-slate-800 border-slate-600 text-white"
              />
              <Button onClick={addIndustry} size="sm" variant="outline">
                <Plus className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {context.industry_focus.map((industry, index) => (
                <Badge key={index} variant="secondary" className="bg-green-700 text-white">
                  {industry}
                  <Button
                    onClick={() => removeIndustry(index)}
                    variant="ghost"
                    size="sm"
                    className="ml-2 h-4 w-4 p-0 hover:bg-green-600"
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
            {context.industry_focus.length === 0 && (
              <p className="text-slate-500 text-sm mt-2">
                Add industry sectors to help agents focus on relevant leads
              </p>
            )}
          </div>
        </div>

        {/* Context Summary */}
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <h4 className="text-white font-medium mb-2">Context Summary</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-slate-400">Pain Points:</span>
              <span className="text-white ml-2">{context.pain_points.length}</span>
            </div>
            <div>
              <span className="text-slate-400">Industries:</span>
              <span className="text-white ml-2">{context.industry_focus.length}</span>
            </div>
            <div>
              <span className="text-slate-400">Completeness:</span>
              <span className="text-white ml-2">
                {Math.round(
                  ([
                    context.business_description,
                    context.target_market,
                    context.value_proposition,
                    context.pain_points.length > 0,
                    context.industry_focus.length > 0
                  ].filter(Boolean).length / 5) * 100
                )}%
              </span>
            </div>
          </div>
        </div>

        {hasChanges && (
          <Alert className="bg-yellow-900/20 border-yellow-700">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-yellow-300">
              You have unsaved changes. Click "Save Context" to apply them.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};
