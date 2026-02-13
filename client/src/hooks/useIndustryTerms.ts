import { useMemo } from 'react';
import { useFounderStore } from '@/store/founderStore';

export interface IndustryTerms {
  customer: string;
  customers: string;
  revenue: string;
  product: string;
  churn: string;
  acquisition: string;
  unit: string;
}

const TERM_MAP: Record<string, Partial<IndustryTerms>> = {
  healthcare: { customer: 'patient', customers: 'patients', revenue: 'revenue', product: 'service', churn: 'patient attrition', acquisition: 'patient acquisition', unit: 'case' },
  edtech: { customer: 'learner', customers: 'learners', revenue: 'revenue', product: 'course', churn: 'dropout rate', acquisition: 'enrollment', unit: 'enrollment' },
  d2c: { customer: 'buyer', customers: 'buyers', revenue: 'sales', product: 'product', churn: 'repeat drop-off', acquisition: 'customer acquisition', unit: 'order' },
  food: { customer: 'customer', customers: 'customers', revenue: 'sales', product: 'product', churn: 'customer loss', acquisition: 'customer acquisition', unit: 'order' },
  real_estate: { customer: 'tenant', customers: 'tenants', revenue: 'rental income', product: 'property', churn: 'vacancy rate', acquisition: 'tenant acquisition', unit: 'unit' },
  logistics: { customer: 'shipper', customers: 'shippers', revenue: 'freight revenue', product: 'shipment', churn: 'shipper churn', acquisition: 'shipper acquisition', unit: 'shipment' },
  media: { customer: 'subscriber', customers: 'subscribers', revenue: 'ad + subscription revenue', product: 'content', churn: 'subscriber churn', acquisition: 'subscriber acquisition', unit: 'impression' },
  marketplace: { customer: 'user', customers: 'users', revenue: 'GMV / take-rate', product: 'listing', churn: 'user churn', acquisition: 'user acquisition', unit: 'transaction' },
  climate: { customer: 'customer', customers: 'customers', revenue: 'revenue', product: 'solution', churn: 'contract loss', acquisition: 'customer acquisition', unit: 'installation' },
  agritech: { customer: 'farmer', customers: 'farmers', revenue: 'revenue', product: 'solution', churn: 'farmer attrition', acquisition: 'farmer onboarding', unit: 'farm' },
  deeptech: { customer: 'client', customers: 'clients', revenue: 'contract revenue', product: 'product', churn: 'client churn', acquisition: 'client acquisition', unit: 'unit' },
};

const DEFAULT_TERMS: IndustryTerms = {
  customer: 'customer',
  customers: 'customers',
  revenue: 'revenue',
  product: 'product',
  churn: 'churn',
  acquisition: 'customer acquisition',
  unit: 'unit',
};

export function useIndustryTerms(): IndustryTerms {
  const { currentCompany } = useFounderStore();
  const industry = (currentCompany as any)?.industry || 'general_saas';

  return useMemo(() => {
    const overrides = TERM_MAP[industry];
    if (!overrides) return DEFAULT_TERMS;
    return { ...DEFAULT_TERMS, ...overrides };
  }, [industry]);
}
