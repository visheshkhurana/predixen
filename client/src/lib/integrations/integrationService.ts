import { 
  IntegrationConfig, 
  ConnectedIntegration, 
  SyncResult, 
  SyncedDataPoint,
  EncryptedCredentials,
  SyncInterval 
} from './types';
import { getIntegrationById } from './registry';

class IntegrationService {
  private connectedIntegrations: Map<string, ConnectedIntegration> = new Map();

  async connect(
    integrationId: string, 
    userId: string, 
    companyId: string,
    credentials: EncryptedCredentials,
    selectedDataPoints: string[]
  ): Promise<ConnectedIntegration> {
    const integration = getIntegrationById(integrationId);
    if (!integration) {
      throw new Error(`Integration ${integrationId} not found`);
    }

    const connected: ConnectedIntegration = {
      id: `${companyId}-${integrationId}`,
      integrationId,
      userId,
      companyId,
      status: 'connected',
      connectedAt: new Date(),
      syncInterval: integration.syncConfig.defaultInterval,
      credentials,
      selectedDataPoints,
    };

    this.connectedIntegrations.set(connected.id, connected);
    
    await this.sync(connected.id);

    return connected;
  }

  async disconnect(connectionId: string): Promise<void> {
    const connection = this.connectedIntegrations.get(connectionId);
    if (!connection) {
      throw new Error(`Connection ${connectionId} not found`);
    }

    this.connectedIntegrations.delete(connectionId);
  }

  async sync(connectionId: string): Promise<SyncResult> {
    const connection = this.connectedIntegrations.get(connectionId);
    if (!connection) {
      throw new Error(`Connection ${connectionId} not found`);
    }

    const integration = getIntegrationById(connection.integrationId);
    if (!integration) {
      throw new Error(`Integration ${connection.integrationId} not found`);
    }

    try {
      connection.status = 'syncing';

      const dataPoints = await this.fetchDataPoints(integration, connection);

      connection.lastSyncAt = new Date();
      connection.status = 'connected';
      connection.nextSyncAt = this.calculateNextSync(connection.syncInterval);

      return {
        integrationId: connection.integrationId,
        success: true,
        syncedAt: new Date(),
        recordsProcessed: dataPoints.length,
        dataPoints,
      };
    } catch (error) {
      connection.status = 'error';
      connection.error = error instanceof Error ? error.message : 'Unknown error';
      
      return {
        integrationId: connection.integrationId,
        success: false,
        syncedAt: new Date(),
        recordsProcessed: 0,
        errors: [{ dataPoint: 'all', error: connection.error, timestamp: new Date() }],
        dataPoints: [],
      };
    }
  }

  private async fetchDataPoints(
    integration: IntegrationConfig, 
    connection: ConnectedIntegration
  ): Promise<SyncedDataPoint[]> {
    switch (integration.id) {
      case 'google-sheets':
        return this.fetchGoogleSheetsData(connection);
      case 'google-analytics-4':
        return this.fetchGoogleAnalyticsData(connection);
      case 'mixpanel':
        return this.fetchMixpanelData(connection);
      case 'chartmogul':
        return this.fetchChartMogulData(connection);
      case 'stripe':
        return this.fetchStripeData(connection);
      default:
        throw new Error(`No handler for integration ${integration.id}`);
    }
  }

  private async fetchGoogleSheetsData(connection: ConnectedIntegration): Promise<SyncedDataPoint[]> {
    return [];
  }

  private async fetchGoogleAnalyticsData(connection: ConnectedIntegration): Promise<SyncedDataPoint[]> {
    return [];
  }

  private async fetchMixpanelData(connection: ConnectedIntegration): Promise<SyncedDataPoint[]> {
    return [];
  }

  private async fetchChartMogulData(connection: ConnectedIntegration): Promise<SyncedDataPoint[]> {
    return [];
  }

  private async fetchStripeData(connection: ConnectedIntegration): Promise<SyncedDataPoint[]> {
    return [];
  }

  private calculateNextSync(interval: SyncInterval): Date {
    const now = new Date();
    switch (interval) {
      case '5min': return new Date(now.getTime() + 5 * 60 * 1000);
      case '15min': return new Date(now.getTime() + 15 * 60 * 1000);
      case '30min': return new Date(now.getTime() + 30 * 60 * 1000);
      case 'hourly': return new Date(now.getTime() + 60 * 60 * 1000);
      case 'daily': return new Date(now.getTime() + 24 * 60 * 60 * 1000);
      case 'weekly': return new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
      default: return new Date(now.getTime() + 60 * 60 * 1000);
    }
  }

  getConnectionsByCompany(companyId: string): ConnectedIntegration[] {
    return Array.from(this.connectedIntegrations.values())
      .filter(c => c.companyId === companyId);
  }

  getConnectionStatus(connectionId: string): ConnectedIntegration | undefined {
    return this.connectedIntegrations.get(connectionId);
  }

  isConnected(integrationId: string, companyId: string): boolean {
    const connectionId = `${companyId}-${integrationId}`;
    return this.connectedIntegrations.has(connectionId);
  }
}

export const integrationService = new IntegrationService();
