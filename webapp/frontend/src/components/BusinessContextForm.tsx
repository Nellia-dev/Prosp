import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod'; // Assuming Zod for schema validation
import { useTranslation } from '../hooks/useTranslation';
import { Button } from "@/components/ui/button"; // Assuming shadcn/ui components
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useCreateBusinessContext } from '../hooks/api/useBusinessContext';
// import { toast } from 'sonner'; // Or your preferred toast library

// Placeholder Zod schema - replace with your actual schema
const businessContextSchema = z.object({
  business_description: z.string().min(10, { message: "business_description_error" }),
  product_service_description: z.string().min(10, { message: "product_service_description_error" }),
  target_market: z.string().min(5, { message: "target_market_error" }),
  value_proposition: z.string().min(10, { message: "value_proposition_error" }),
  ideal_customer: z.string().min(10, { message: "ideal_customer_error" }),
  pain_points: z.string().min(10, { message: "pain_points_error" }),
  competitive_advantage: z.string().optional(),
  competitors: z.string().optional(),
  industry_focus: z.string().min(3, { message: "industry_focus_error" }),
  geographic_focus: z.string().optional(),
});

export type BusinessContextFormData = z.infer<typeof businessContextSchema>;

interface BusinessContextFormProps {
  onComplete: () => void;
}

export const BusinessContextForm = ({ onComplete }: BusinessContextFormProps) => {
  const { t } = useTranslation();
  const { mutate: saveContext, isPending } = useCreateBusinessContext();

  const form = useForm<BusinessContextFormData>({
    resolver: zodResolver(businessContextSchema),
    defaultValues: {
      business_description: '',
      product_service_description: '',
      target_market: '',
      value_proposition: '',
      ideal_customer: '',
      pain_points: '',
      competitive_advantage: '',
      competitors: '',
      industry_focus: '',
      geographic_focus: '',
    },
  });

  const onSubmit = (data: BusinessContextFormData) => {
    const requestData = {
      business_description: data.business_description,
      product_service_description: data.product_service_description,
      target_market: data.target_market,
      value_proposition: data.value_proposition,
      ideal_customer: data.ideal_customer,
      pain_points: data.pain_points.split(',').map(p => p.trim()),
      competitive_advantage: data.competitive_advantage,
      competitors: data.competitors?.split(',').map(c => c.trim()) || [],
      industry_focus: data.industry_focus.split(',').map(i => i.trim()),
      geographic_focus: data.geographic_focus?.split(',').map(g => g.trim()) || [],
    };
    saveContext(requestData, {
      onSuccess: () => {
        console.log(t('businessContext.form.success'));
        onComplete();
      },
      onError: (error: Error) => {
        console.error(t('businessContext.form.error'), error);
      }
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 p-6 bg-slate-800 rounded-lg shadow-xl border border-slate-700">
        <FormField
          control={form.control}
          name="business_description"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('business_description')}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder={t('business_description')}
                  {...field}
                  className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500 min-h-[100px]"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="product_service_description"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('product_service_description')}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder={t('product_service_description')}
                  {...field}
                  className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500 min-h-[100px]"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="target_market"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('target_market')}</FormLabel>
              <FormControl>
                <Input placeholder={t('target_market')} {...field} className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="value_proposition"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('value_proposition')}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder={t('value_proposition')}
                  {...field}
                  className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500 min-h-[100px]"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="ideal_customer"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('ideal_customer')}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder={t('ideal_customer')}
                  {...field}
                  className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500 min-h-[100px]"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="pain_points"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('pain_points')}</FormLabel>
              <FormControl>
                <Input placeholder={t('pain_points')} {...field} className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="industry_focus"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('industry_focus')}</FormLabel>
              <FormControl>
                <Input placeholder={t('industry_focus')} {...field} className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={isPending} className="w-full bg-green-600 hover:bg-green-700 text-white">
          {isPending ? t('common.saving') : t('common.saveContext')}
        </Button>
      </form>
    </Form>
  );
};
