export type IntegrationCategory = 
  | 'accounting'
  | 'payroll'
  | 'erp'
  | 'crm'
  | 'payments'
  | 'analytics'
  | 'marketing'
  | 'support'
  | 'databases'
  | 'spreadsheets'
  | 'productivity';

export type IntegrationStatus = 'connected' | 'disconnected' | 'error' | 'syncing';

export type AuthType = 'oauth2' | 'api_key' | 'basic_auth' | 'service_account';

export interface IntegrationConfig {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: IntegrationCategory;
  authType: AuthType;
  status: IntegrationStatus;
  isComingSoon?: boolean;
  
  oauthConfig?: {
    authUrl: string;
    tokenUrl: string;
    scopes: string[];
    clientId?: string;
  };
  
  apiKeyConfig?: {
    fields: ApiKeyField[];
  };
  
  dataPoints: DataPoint[];
  
  syncConfig: {
    defaultInterval: SyncInterval;
    availableIntervals: SyncInterval[];
    supportsRealtime: boolean;
  };
}

export interface ApiKeyField {
  name: string;
  label: string;
  type: 'text' | 'password' | 'url';
  required: boolean;
  placeholder?: string;
  helpText?: string;
}

export interface DataPoint {
  id: string;
  name: string;
  description: string;
  dataType: 'number' | 'currency' | 'percentage' | 'string' | 'date' | 'boolean';
  category: string;
  refreshRate: 'realtime' | 'hourly' | 'daily' | 'weekly';
}

export type SyncInterval = '5min' | '15min' | '30min' | 'hourly' | 'daily' | 'weekly';

export interface ConnectedIntegration {
  id: string;
  integrationId: string;
  userId: string;
  companyId: string;
  status: IntegrationStatus;
  connectedAt: Date;
  lastSyncAt?: Date;
  nextSyncAt?: Date;
  syncInterval: SyncInterval;
  credentials: EncryptedCredentials;
  selectedDataPoints: string[];
  error?: string;
}

export interface EncryptedCredentials {
  accessToken?: string;
  refreshToken?: string;
  apiKey?: string;
  additionalFields?: Record<string, string>;
  expiresAt?: Date;
}

export interface SyncResult {
  integrationId: string;
  success: boolean;
  syncedAt: Date;
  recordsProcessed: number;
  errors?: SyncError[];
  dataPoints: SyncedDataPoint[];
}

export interface SyncError {
  dataPoint: string;
  error: string;
  timestamp: Date;
}

export interface SyncedDataPoint {
  dataPointId: string;
  value: any;
  previousValue?: any;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface SheetMapping {
  spreadsheetId: string;
  spreadsheetName: string;
  sheetId: string;
  sheetName: string;
  dataRange: string;
  columnMappings: ColumnMapping[];
  hasHeaderRow: boolean;
  syncInterval: SyncInterval;
}

export interface ColumnMapping {
  columnIndex: number;
  columnLetter: string;
  columnHeader: string;
  metricName: string;
  dataType: 'number' | 'currency' | 'percentage' | 'string' | 'date';
  aggregation?: 'sum' | 'average' | 'latest' | 'min' | 'max';
}

export interface SpreadsheetInfo {
  id: string;
  name: string;
  sheets: SheetInfo[];
  lastModified: string;
}

export interface SheetInfo {
  id: number;
  name: string;
  rowCount: number;
  columnCount: number;
}
