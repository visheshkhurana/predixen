import { IntegrationConfig, IntegrationCategory } from './types';

export const googleSheetsIntegration: IntegrationConfig = {
  id: 'google-sheets',
  name: 'Google Sheets',
  description: 'Import data from Google Sheets spreadsheets. Perfect for custom metrics, budgets, and manual data entry.',
  icon: 'sheets',
  category: 'spreadsheets',
  authType: 'oauth2',
  status: 'disconnected',
  
  oauthConfig: {
    authUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
    tokenUrl: 'https://oauth2.googleapis.com/token',
    scopes: [
      'https://www.googleapis.com/auth/spreadsheets.readonly',
      'https://www.googleapis.com/auth/drive.readonly'
    ],
  },
  
  dataPoints: [
    {
      id: 'custom_metric',
      name: 'Custom Metrics',
      description: 'Import any numeric data from your spreadsheets',
      dataType: 'number',
      category: 'custom',
      refreshRate: 'hourly',
    },
    {
      id: 'budget_data',
      name: 'Budget Data',
      description: 'Import budget and forecast data',
      dataType: 'currency',
      category: 'finance',
      refreshRate: 'daily',
    },
    {
      id: 'manual_kpis',
      name: 'Manual KPIs',
      description: 'Track KPIs that you enter manually',
      dataType: 'number',
      category: 'kpi',
      refreshRate: 'daily',
    },
  ],
  
  syncConfig: {
    defaultInterval: 'hourly',
    availableIntervals: ['15min', '30min', 'hourly', 'daily'],
    supportsRealtime: false,
  },
};

export const googleAnalyticsIntegration: IntegrationConfig = {
  id: 'google-analytics-4',
  name: 'Google Analytics 4',
  description: 'Track website traffic, user acquisition, and conversion funnels.',
  icon: 'analytics',
  category: 'analytics',
  authType: 'oauth2',
  status: 'disconnected',
  
  oauthConfig: {
    authUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
    tokenUrl: 'https://oauth2.googleapis.com/token',
    scopes: [
      'https://www.googleapis.com/auth/analytics.readonly',
    ],
  },
  
  dataPoints: [
    { id: 'sessions', name: 'Sessions', description: 'Total website sessions', dataType: 'number', category: 'traffic', refreshRate: 'hourly' },
    { id: 'users', name: 'Users', description: 'Unique users', dataType: 'number', category: 'traffic', refreshRate: 'hourly' },
    { id: 'new_users', name: 'New Users', description: 'First-time visitors', dataType: 'number', category: 'traffic', refreshRate: 'hourly' },
    { id: 'bounce_rate', name: 'Bounce Rate', description: 'Single-page session percentage', dataType: 'percentage', category: 'engagement', refreshRate: 'hourly' },
    { id: 'avg_session_duration', name: 'Avg Session Duration', description: 'Average time on site', dataType: 'number', category: 'engagement', refreshRate: 'hourly' },
    { id: 'page_views', name: 'Page Views', description: 'Total page views', dataType: 'number', category: 'traffic', refreshRate: 'hourly' },
    { id: 'conversions', name: 'Conversions', description: 'Goal completions', dataType: 'number', category: 'conversion', refreshRate: 'hourly' },
    { id: 'conversion_rate', name: 'Conversion Rate', description: 'Conversion percentage', dataType: 'percentage', category: 'conversion', refreshRate: 'hourly' },
  ],
  
  syncConfig: {
    defaultInterval: 'hourly',
    availableIntervals: ['hourly', 'daily'],
    supportsRealtime: false,
  },
};

export const mixpanelIntegration: IntegrationConfig = {
  id: 'mixpanel',
  name: 'Mixpanel',
  description: 'Product analytics for user behavior, retention, and feature engagement.',
  icon: 'mixpanel',
  category: 'analytics',
  authType: 'api_key',
  status: 'disconnected',
  
  apiKeyConfig: {
    fields: [
      { name: 'project_id', label: 'Project ID', type: 'text', required: true, placeholder: 'Your Mixpanel Project ID' },
      { name: 'api_secret', label: 'API Secret', type: 'password', required: true, placeholder: 'Your API Secret' },
    ],
  },
  
  dataPoints: [
    { id: 'dau', name: 'Daily Active Users', description: 'Users active today', dataType: 'number', category: 'users', refreshRate: 'daily' },
    { id: 'mau', name: 'Monthly Active Users', description: 'Users active this month', dataType: 'number', category: 'users', refreshRate: 'daily' },
    { id: 'dau_mau_ratio', name: 'DAU/MAU Ratio', description: 'Stickiness metric', dataType: 'percentage', category: 'engagement', refreshRate: 'daily' },
    { id: 'retention_d1', name: 'D1 Retention', description: 'Day 1 retention rate', dataType: 'percentage', category: 'retention', refreshRate: 'daily' },
    { id: 'retention_d7', name: 'D7 Retention', description: 'Day 7 retention rate', dataType: 'percentage', category: 'retention', refreshRate: 'daily' },
    { id: 'retention_d30', name: 'D30 Retention', description: 'Day 30 retention rate', dataType: 'percentage', category: 'retention', refreshRate: 'daily' },
  ],
  
  syncConfig: {
    defaultInterval: 'daily',
    availableIntervals: ['hourly', 'daily'],
    supportsRealtime: false,
  },
};

export const chartMogulIntegration: IntegrationConfig = {
  id: 'chartmogul',
  name: 'ChartMogul',
  description: 'Subscription analytics - MRR, ARR, churn, LTV from your billing data.',
  icon: 'chartmogul',
  category: 'analytics',
  authType: 'api_key',
  status: 'disconnected',
  
  apiKeyConfig: {
    fields: [
      { name: 'api_key', label: 'API Key', type: 'password', required: true, placeholder: 'Your ChartMogul API Key' },
    ],
  },
  
  dataPoints: [
    { id: 'mrr', name: 'MRR', description: 'Monthly Recurring Revenue', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
    { id: 'arr', name: 'ARR', description: 'Annual Recurring Revenue', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
    { id: 'mrr_growth_rate', name: 'MRR Growth Rate', description: 'Month-over-month MRR growth', dataType: 'percentage', category: 'revenue', refreshRate: 'daily' },
    { id: 'net_mrr_churn', name: 'Net MRR Churn', description: 'Net revenue churn rate', dataType: 'percentage', category: 'churn', refreshRate: 'daily' },
    { id: 'gross_mrr_churn', name: 'Gross MRR Churn', description: 'Gross revenue churn rate', dataType: 'percentage', category: 'churn', refreshRate: 'daily' },
    { id: 'customer_churn', name: 'Customer Churn', description: 'Logo churn rate', dataType: 'percentage', category: 'churn', refreshRate: 'daily' },
    { id: 'ltv', name: 'LTV', description: 'Customer Lifetime Value', dataType: 'currency', category: 'unit_economics', refreshRate: 'daily' },
    { id: 'arpa', name: 'ARPA', description: 'Average Revenue Per Account', dataType: 'currency', category: 'unit_economics', refreshRate: 'daily' },
    { id: 'customers', name: 'Total Customers', description: 'Active paying customers', dataType: 'number', category: 'customers', refreshRate: 'daily' },
    { id: 'new_mrr', name: 'New MRR', description: 'MRR from new customers', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
    { id: 'expansion_mrr', name: 'Expansion MRR', description: 'MRR from upgrades', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
    { id: 'contraction_mrr', name: 'Contraction MRR', description: 'MRR lost to downgrades', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
  ],
  
  syncConfig: {
    defaultInterval: 'daily',
    availableIntervals: ['hourly', 'daily'],
    supportsRealtime: false,
  },
};

export const stripeIntegration: IntegrationConfig = {
  id: 'stripe',
  name: 'Stripe',
  description: 'Payment processing data - revenue, subscriptions, and customer metrics.',
  icon: 'stripe',
  category: 'payments',
  authType: 'api_key',
  status: 'disconnected',
  
  apiKeyConfig: {
    fields: [
      { name: 'api_key', label: 'Stripe Secret Key', type: 'password', required: true, placeholder: 'sk_live_...' },
    ],
  },
  
  dataPoints: [
    { id: 'mrr', name: 'MRR', description: 'Monthly Recurring Revenue', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
    { id: 'total_revenue', name: 'Total Revenue', description: 'All-time revenue', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
    { id: 'active_subscriptions', name: 'Active Subscriptions', description: 'Current active subscriptions', dataType: 'number', category: 'subscriptions', refreshRate: 'daily' },
    { id: 'new_customers', name: 'New Customers', description: 'New customers this month', dataType: 'number', category: 'customers', refreshRate: 'daily' },
  ],
  
  syncConfig: {
    defaultInterval: 'daily',
    availableIntervals: ['hourly', 'daily'],
    supportsRealtime: false,
  },
};

export const hubspotIntegration: IntegrationConfig = {
  id: 'hubspot',
  name: 'HubSpot',
  description: 'CRM data - deals, contacts, and sales pipeline metrics.',
  icon: 'hubspot',
  category: 'crm',
  authType: 'oauth2',
  status: 'disconnected',
  isComingSoon: true,
  
  oauthConfig: {
    authUrl: 'https://app.hubspot.com/oauth/authorize',
    tokenUrl: 'https://api.hubapi.com/oauth/v1/token',
    scopes: ['crm.objects.deals.read', 'crm.objects.contacts.read'],
  },
  
  dataPoints: [
    { id: 'total_deals', name: 'Total Deals', description: 'All deals in pipeline', dataType: 'number', category: 'sales', refreshRate: 'daily' },
    { id: 'pipeline_value', name: 'Pipeline Value', description: 'Total pipeline value', dataType: 'currency', category: 'sales', refreshRate: 'daily' },
    { id: 'contacts', name: 'Total Contacts', description: 'All contacts', dataType: 'number', category: 'contacts', refreshRate: 'daily' },
  ],
  
  syncConfig: {
    defaultInterval: 'daily',
    availableIntervals: ['hourly', 'daily'],
    supportsRealtime: false,
  },
};

export const salesforceIntegration: IntegrationConfig = {
  id: 'salesforce',
  name: 'Salesforce',
  description: 'Enterprise CRM - opportunities, accounts, and forecasting.',
  icon: 'salesforce',
  category: 'crm',
  authType: 'oauth2',
  status: 'disconnected',
  isComingSoon: true,
  
  oauthConfig: {
    authUrl: 'https://login.salesforce.com/services/oauth2/authorize',
    tokenUrl: 'https://login.salesforce.com/services/oauth2/token',
    scopes: ['api', 'refresh_token'],
  },
  
  dataPoints: [
    { id: 'opportunities', name: 'Open Opportunities', description: 'Active sales opportunities', dataType: 'number', category: 'sales', refreshRate: 'daily' },
    { id: 'won_revenue', name: 'Won Revenue', description: 'Closed won revenue', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
    { id: 'forecast', name: 'Sales Forecast', description: 'Forecasted revenue', dataType: 'currency', category: 'forecast', refreshRate: 'daily' },
  ],
  
  syncConfig: {
    defaultInterval: 'daily',
    availableIntervals: ['hourly', 'daily'],
    supportsRealtime: false,
  },
};

export const quickbooksIntegration: IntegrationConfig = {
  id: 'quickbooks',
  name: 'QuickBooks',
  description: 'Accounting data - P&L, balance sheet, and cash flow.',
  icon: 'quickbooks',
  category: 'accounting',
  authType: 'oauth2',
  status: 'disconnected',
  isComingSoon: true,
  
  oauthConfig: {
    authUrl: 'https://appcenter.intuit.com/connect/oauth2',
    tokenUrl: 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer',
    scopes: ['com.intuit.quickbooks.accounting'],
  },
  
  dataPoints: [
    { id: 'revenue', name: 'Revenue', description: 'Total revenue', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
    { id: 'expenses', name: 'Expenses', description: 'Total expenses', dataType: 'currency', category: 'expenses', refreshRate: 'daily' },
    { id: 'net_income', name: 'Net Income', description: 'Net income', dataType: 'currency', category: 'profit', refreshRate: 'daily' },
    { id: 'cash', name: 'Cash Balance', description: 'Current cash balance', dataType: 'currency', category: 'assets', refreshRate: 'daily' },
  ],
  
  syncConfig: {
    defaultInterval: 'daily',
    availableIntervals: ['daily', 'weekly'],
    supportsRealtime: false,
  },
};

export const xeroIntegration: IntegrationConfig = {
  id: 'xero',
  name: 'Xero',
  description: 'Cloud accounting - invoices, expenses, and bank reconciliation.',
  icon: 'xero',
  category: 'accounting',
  authType: 'oauth2',
  status: 'disconnected',
  isComingSoon: true,
  
  oauthConfig: {
    authUrl: 'https://login.xero.com/identity/connect/authorize',
    tokenUrl: 'https://identity.xero.com/connect/token',
    scopes: ['openid', 'profile', 'email', 'accounting.transactions.read'],
  },
  
  dataPoints: [
    { id: 'revenue', name: 'Revenue', description: 'Total revenue', dataType: 'currency', category: 'revenue', refreshRate: 'daily' },
    { id: 'expenses', name: 'Expenses', description: 'Total expenses', dataType: 'currency', category: 'expenses', refreshRate: 'daily' },
    { id: 'bank_balance', name: 'Bank Balance', description: 'Total bank balance', dataType: 'currency', category: 'assets', refreshRate: 'daily' },
  ],
  
  syncConfig: {
    defaultInterval: 'daily',
    availableIntervals: ['daily', 'weekly'],
    supportsRealtime: false,
  },
};

export const integrationRegistry: IntegrationConfig[] = [
  googleSheetsIntegration,
  googleAnalyticsIntegration,
  mixpanelIntegration,
  chartMogulIntegration,
  stripeIntegration,
  hubspotIntegration,
  salesforceIntegration,
  quickbooksIntegration,
  xeroIntegration,
];

export function getIntegrationById(id: string): IntegrationConfig | undefined {
  return integrationRegistry.find(i => i.id === id);
}

export function getIntegrationsByCategory(category: IntegrationCategory): IntegrationConfig[] {
  return integrationRegistry.filter(i => i.category === category);
}

export function getActiveIntegrations(): IntegrationConfig[] {
  return integrationRegistry.filter(i => !i.isComingSoon);
}

export function getComingSoonIntegrations(): IntegrationConfig[] {
  return integrationRegistry.filter(i => i.isComingSoon);
}
