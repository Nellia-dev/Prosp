export type PlanId = 'free' | 'starter' | 'pro' | 'enterprise';

export interface PlanDetails {
  id: PlanId;
  name: string;
  quota: number; // Max leads
  period: 'day' | 'week' | 'month'; // Quota reset period
  price: number | null; // Price in smallest currency unit (e.g., cents) or null for custom
}

export const PLANS: Record<PlanId, PlanDetails> = {
  free: { 
    id: 'free', 
    name: 'Free', 
    quota: 10, 
    period: 'week', 
    price: 0 
  },
  starter: { 
    id: 'starter', 
    name: 'Starter', 
    quota: 75, 
    period: 'day', 
    price: 4900 // $49.00 in cents
  },
  pro: { 
    id: 'pro', 
    name: 'PRO', 
    quota: 500, 
    period: 'day', 
    price: 19900 // $199.00 in cents
  },
  enterprise: { 
    id: 'enterprise', 
    name: 'Enterprise', 
    quota: Infinity, 
    period: 'month', 
    price: null // Custom pricing
  },
};

export const DEFAULT_PLAN: PlanId = 'free';
