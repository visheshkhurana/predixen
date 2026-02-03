import { z } from "zod";

export const AuthTypeEnum = z.enum([
  "oauth",
  "api_key", 
  "webhook",
  "db_connection",
  "file_upload"
]);

export const CategoryEnum = z.enum([
  "Finance",
  "Marketing", 
  "CRM",
  "Databases",
  "Files",
  "Payroll",
  "ERP",
  "Analytics",
  "Custom"
]);

export const SetupComplexityEnum = z.enum(["low", "medium", "high"]);

export const RefreshCadenceEnum = z.enum([
  "real-time",
  "hourly", 
  "daily",
  "manual"
]);

export const connectorSchema = z.object({
  id: z.string(),
  name: z.string(),
  category: CategoryEnum,
  logoUrl: z.string().optional(),
  description: z.string(),
  longDescription: z.string().optional(),
  authType: AuthTypeEnum,
  supportsWebhooks: z.boolean().default(false),
  supportsPolling: z.boolean().default(true),
  supportsIncremental: z.boolean().default(false),
  typicalRefresh: RefreshCadenceEnum,
  native: z.boolean().default(false),
  beta: z.boolean().default(false),
  popularityRank: z.number().default(100),
  setupComplexity: SetupComplexityEnum.default("medium"),
  documentationUrl: z.string().optional(),
  implemented: z.boolean().default(false),
  adapterKey: z.string().optional(),
  metricsUnlocked: z.array(z.string()).default([]),
  requiredPermissions: z.array(z.string()).default([]),
  dataCollected: z.array(z.string()).default([]),
});

export type Connector = z.infer<typeof connectorSchema>;
export type AuthType = z.infer<typeof AuthTypeEnum>;
export type Category = z.infer<typeof CategoryEnum>;
export type SetupComplexity = z.infer<typeof SetupComplexityEnum>;
export type RefreshCadence = z.infer<typeof RefreshCadenceEnum>;

export const connectorStatusSchema = z.object({
  connectorId: z.string(),
  status: z.enum(["active", "error", "paused", "not_installed"]),
  lastSync: z.string().nullable(),
  nextSync: z.string().nullable(),
  errorSummary: z.string().nullable(),
  recordCount: z.number().default(0),
});

export type ConnectorStatus = z.infer<typeof connectorStatusSchema>;

export const catalogConnectorSchema = connectorSchema.extend({
  installStatus: connectorStatusSchema.optional(),
});

export type CatalogConnector = z.infer<typeof catalogConnectorSchema>;

export const insertDataSourceSchema = z.object({
  connectorId: z.string(),
  name: z.string(),
  config: z.record(z.any()).optional(),
  syncMode: z.enum(["webhook", "poll"]).default("poll"),
  refreshFrequency: z.enum(["real-time", "hourly", "daily", "manual"]).default("daily"),
});

export type InsertDataSource = z.infer<typeof insertDataSourceSchema>;
