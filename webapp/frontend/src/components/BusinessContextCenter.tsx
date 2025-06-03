
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Save, Plus, X } from "lucide-react";
import { BusinessContext } from "../types/nellia";
import { useTranslation } from "../hooks/useTranslation";

export const BusinessContextCenter = () => {
  const { t } = useTranslation();
  const [context, setContext] = useState<BusinessContext>({
    business_description: '',
    target_market: '',
    value_proposition: '',
    ideal_customer: '',
    pain_points: [],
    competitive_advantage: '',
    industry_focus: [],
    geographic_focus: ['Brasil']
  });

  const [newPainPoint, setNewPainPoint] = useState('');
  const [newIndustry, setNewIndustry] = useState('');

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

  const handleSave = () => {
    console.log('Saving business context:', context);
    // Here you would typically send to your backend
  };

  return (
    <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-white text-lg">{t('business_context')}</CardTitle>
          <Button onClick={handleSave} size="sm" className="bg-green-600 hover:bg-green-700">
            <Save className="w-4 h-4 mr-2" />
            Salvar
          </Button>
        </div>
        <p className="text-slate-400 text-sm">
          Configure o contexto do seu negócio para otimizar o processamento de leads
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-white text-sm font-medium">{t('business_description')}</label>
            <Textarea
              value={context.business_description}
              onChange={(e) => setContext(prev => ({ ...prev, business_description: e.target.value }))}
              placeholder="Descreva seu negócio, produtos e serviços..."
              className="bg-slate-800 border-slate-600 text-white min-h-[100px]"
            />
          </div>

          <div className="space-y-2">
            <label className="text-white text-sm font-medium">{t('target_market')}</label>
            <Textarea
              value={context.target_market}
              onChange={(e) => setContext(prev => ({ ...prev, target_market: e.target.value }))}
              placeholder="Defina seu mercado-alvo..."
              className="bg-slate-800 border-slate-600 text-white min-h-[100px]"
            />
          </div>

          <div className="space-y-2">
            <label className="text-white text-sm font-medium">{t('value_proposition')}</label>
            <Textarea
              value={context.value_proposition}
              onChange={(e) => setContext(prev => ({ ...prev, value_proposition: e.target.value }))}
              placeholder="Qual é sua proposta de valor única?"
              className="bg-slate-800 border-slate-600 text-white"
            />
          </div>

          <div className="space-y-2">
            <label className="text-white text-sm font-medium">{t('ideal_customer')}</label>
            <Textarea
              value={context.ideal_customer}
              onChange={(e) => setContext(prev => ({ ...prev, ideal_customer: e.target.value }))}
              placeholder="Descreva seu cliente ideal..."
              className="bg-slate-800 border-slate-600 text-white"
            />
          </div>

          <div className="space-y-2">
            <label className="text-white text-sm font-medium">{t('competitive_advantage')}</label>
            <Textarea
              value={context.competitive_advantage}
              onChange={(e) => setContext(prev => ({ ...prev, competitive_advantage: e.target.value }))}
              placeholder="Qual é sua vantagem competitiva?"
              className="bg-slate-800 border-slate-600 text-white"
            />
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-white text-sm font-medium mb-2 block">{t('pain_points')}</label>
            <div className="flex space-x-2 mb-3">
              <Input
                value={newPainPoint}
                onChange={(e) => setNewPainPoint(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addPainPoint()}
                placeholder="Adicionar ponto de dor que você resolve..."
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
          </div>

          <div>
            <label className="text-white text-sm font-medium mb-2 block">Setores de Foco</label>
            <div className="flex space-x-2 mb-3">
              <Input
                value={newIndustry}
                onChange={(e) => setNewIndustry(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addIndustry()}
                placeholder="Adicionar setor (ex: E-commerce, SaaS, Fintech...)"
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
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
