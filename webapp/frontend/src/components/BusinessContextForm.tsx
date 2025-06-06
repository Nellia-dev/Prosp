import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod'; // Assuming Zod for schema validation
import { useTranslation } from '../hooks/useTranslation';
import { Button } from "@/components/ui/button"; // Assuming shadcn/ui components
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
// import { toast } from 'sonner'; // Or your preferred toast library

// Placeholder for useCreateBusinessContext hook - should match the one in OnboardingFlow
interface BusinessContextDataPlaceholder {
  businessName?: string; // Made optional
  businessDescription?: string; // Made optional
  targetMarket?: string; // Made optional
  valueProposition?: string; // Made optional
  // Add other fields as per your actual businessContextSchema
  [key: string]: unknown; // Changed any to unknown
}

interface MutationOptionsPlaceholder {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

const useCreateBusinessContext = () => ({
  mutate: (data: BusinessContextDataPlaceholder, options: MutationOptionsPlaceholder) => {
    console.log('Saving business context:', data);
    // Simulate API call
    setTimeout(() => {
      if (options.onSuccess) {
        // toast.success("Business context saved successfully!"); // Uncomment when toast is set up
        console.log("Business context saved successfully!");
        options.onSuccess();
      }
    }, 1000);
  },
  isLoading: false, // Placeholder
});

// Placeholder Zod schema - replace with your actual schema
const businessContextSchema = z.object({
  businessName: z.string().min(2, { message: "Business name must be at least 2 characters." }),
  businessDescription: z.string().min(10, { message: "Description must be at least 10 characters." }),
  targetMarket: z.string().min(5, { message: "Target market must be at least 5 characters." }),
  valueProposition: z.string().min(10, { message: "Value proposition must be at least 10 characters." }),
});

export type BusinessContextFormData = z.infer<typeof businessContextSchema>;

interface BusinessContextFormProps {
  onComplete: () => void;
}

export const BusinessContextForm = ({ onComplete }: BusinessContextFormProps) => {
  const { t } = useTranslation();
  const { mutate: saveContext, isLoading } = useCreateBusinessContext();

  const form = useForm<BusinessContextFormData>({
    resolver: zodResolver(businessContextSchema),
    defaultValues: {
      businessName: '',
      businessDescription: '',
      targetMarket: '',
      valueProposition: '',
    },
  });

  const onSubmit = (data: BusinessContextFormData) => {
    saveContext(data, {
      onSuccess: () => {
        // toast.success(t('businessContext.form.success')); // Use translation for toast
        console.log(t('businessContext.form.success'));
        onComplete();
      },
      onError: (error: Error) => {
        // toast.error(t('businessContext.form.error') + `: ${error.message}`);
        console.error(t('businessContext.form.error'), error);
      }
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 p-6 bg-slate-800 rounded-lg shadow-xl border border-slate-700">
        <FormField
          control={form.control}
          name="businessName"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('businessContext.form.businessName.label')}</FormLabel>
              <FormControl>
                <Input placeholder={t('businessContext.form.businessName.placeholder')} {...field} className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="businessDescription"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('businessContext.form.businessDescription.label')}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder={t('businessContext.form.businessDescription.placeholder')}
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
          name="targetMarket"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('businessContext.form.targetMarket.label')}</FormLabel>
              <FormControl>
                <Input placeholder={t('businessContext.form.targetMarket.placeholder')} {...field} className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        
        <FormField
          control={form.control}
          name="valueProposition"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-slate-200">{t('businessContext.form.valueProposition.label')}</FormLabel>
              <FormControl>
                <Textarea
                  placeholder={t('businessContext.form.valueProposition.placeholder')}
                  {...field}
                  className="bg-slate-700 border-slate-600 text-white placeholder-slate-400 focus:ring-green-500 focus:border-green-500 min-h-[100px]"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={isLoading} className="w-full bg-green-600 hover:bg-green-700 text-white">
          {isLoading ? t('common.saving') : t('common.saveContext')}
        </Button>
      </form>
    </Form>
  );
};
