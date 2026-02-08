"""
Connector Catalog API - The single source of truth for the marketplace UI.
Provides connector metadata, installation status, and sync information.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from server.core.db import get_db

router = APIRouter(prefix="/api/connectors", tags=["connectors"])

class ConnectorMetadata(BaseModel):
    id: str
    name: str
    category: str
    logo_url: Optional[str] = None
    description: str
    long_description: Optional[str] = None
    auth_type: str
    supports_webhooks: bool = False
    supports_polling: bool = True
    supports_incremental: bool = False
    typical_refresh: str
    native: bool = False
    beta: bool = False
    popularity_rank: int = 100
    setup_complexity: str = "medium"
    documentation_url: Optional[str] = None
    implemented: bool = False
    adapter_key: Optional[str] = None
    metrics_unlocked: List[str] = []
    required_permissions: List[str] = []
    data_collected: List[str] = []

class ConnectorStatus(BaseModel):
    connector_id: str
    status: str
    last_sync: Optional[str] = None
    next_sync: Optional[str] = None
    error_summary: Optional[str] = None
    record_count: int = 0

class CatalogConnector(ConnectorMetadata):
    install_status: Optional[ConnectorStatus] = None

CONNECTOR_REGISTRY: List[ConnectorMetadata] = [
    ConnectorMetadata(
        id="stripe",
        name="Stripe",
        category="Finance",
        logo_url="/connectors/stripe.svg",
        description="Payment processing and subscription management",
        long_description="Connect Stripe to automatically sync revenue, subscriptions, invoices, and customer data. Get real-time visibility into MRR, churn, and payment metrics.",
        auth_type="oauth",
        supports_webhooks=True,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="real-time",
        native=True,
        beta=False,
        popularity_rank=1,
        setup_complexity="low",
        documentation_url="https://stripe.com/docs/api",
        implemented=True,
        adapter_key="stripe",
        metrics_unlocked=["MRR", "ARR", "Churn Rate", "Revenue", "Subscription Count", "ARPU"],
        required_permissions=["Read payments", "Read subscriptions", "Read invoices"],
        data_collected=["Payments", "Subscriptions", "Invoices", "Customers", "Refunds"]
    ),
    ConnectorMetadata(
        id="quickbooks",
        name="QuickBooks",
        category="Finance",
        logo_url="/connectors/quickbooks.svg",
        description="Accounting and financial management",
        long_description="Sync your QuickBooks data to get accurate financial statements, expense tracking, and cash flow visibility. Automatically import transactions, invoices, and reports.",
        auth_type="oauth",
        supports_webhooks=True,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="hourly",
        native=True,
        beta=False,
        popularity_rank=2,
        setup_complexity="low",
        documentation_url="https://developer.intuit.com/",
        implemented=True,
        adapter_key="quickbooks",
        metrics_unlocked=["Revenue", "Expenses", "Profit Margin", "Cash Balance", "Accounts Receivable"],
        required_permissions=["Read financial reports", "Access transactions", "View company info"],
        data_collected=["Transactions", "Invoices", "Bills", "Accounts", "Reports"]
    ),
    ConnectorMetadata(
        id="xero",
        name="Xero",
        category="Finance",
        logo_url="/connectors/xero.svg",
        description="Cloud-based accounting software",
        long_description="Connect Xero to sync bank transactions, invoices, expenses, and financial reports. Get a complete picture of your business finances.",
        auth_type="oauth",
        supports_webhooks=True,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="hourly",
        native=True,
        beta=False,
        popularity_rank=3,
        setup_complexity="low",
        documentation_url="https://developer.xero.com/",
        implemented=False,
        metrics_unlocked=["Revenue", "Expenses", "Bank Balance", "Invoice Aging"],
        required_permissions=["Read bank transactions", "Access invoices", "View reports"],
        data_collected=["Transactions", "Invoices", "Bills", "Bank Feeds", "Contacts"]
    ),
    ConnectorMetadata(
        id="hubspot",
        name="HubSpot",
        category="CRM",
        logo_url="/connectors/hubspot.svg",
        description="CRM, marketing, and sales automation",
        long_description="Sync your HubSpot CRM to track deals, contacts, and pipeline. Get insights into sales velocity, conversion rates, and customer lifecycle.",
        auth_type="oauth",
        supports_webhooks=True,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="hourly",
        native=True,
        beta=False,
        popularity_rank=4,
        setup_complexity="low",
        documentation_url="https://developers.hubspot.com/",
        implemented=False,
        metrics_unlocked=["Pipeline Value", "Deal Count", "Win Rate", "Sales Velocity", "CAC"],
        required_permissions=["Read contacts", "Read deals", "Read companies"],
        data_collected=["Contacts", "Deals", "Companies", "Activities", "Lists"]
    ),
    ConnectorMetadata(
        id="salesforce",
        name="Salesforce",
        category="CRM",
        logo_url="/connectors/salesforce.svg",
        description="Enterprise CRM platform",
        long_description="Connect Salesforce to sync opportunities, accounts, and custom objects. Track your entire sales process from lead to close.",
        auth_type="oauth",
        supports_webhooks=True,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="hourly",
        native=True,
        beta=False,
        popularity_rank=5,
        setup_complexity="medium",
        documentation_url="https://developer.salesforce.com/",
        implemented=False,
        metrics_unlocked=["Pipeline Value", "Opportunities", "Win Rate", "Forecast", "CAC"],
        required_permissions=["Read opportunities", "Read accounts", "Read reports"],
        data_collected=["Opportunities", "Accounts", "Contacts", "Leads", "Activities"]
    ),
    ConnectorMetadata(
        id="google_analytics",
        name="Google Analytics",
        category="Analytics",
        logo_url="/connectors/google-analytics.svg",
        description="Web and app analytics",
        long_description="Import Google Analytics data to understand user behavior, acquisition channels, and conversion funnels. Combine with financial data for complete ROI analysis.",
        auth_type="oauth",
        supports_webhooks=False,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="daily",
        native=True,
        beta=False,
        popularity_rank=6,
        setup_complexity="low",
        documentation_url="https://developers.google.com/analytics",
        implemented=False,
        metrics_unlocked=["Sessions", "Users", "Conversion Rate", "Bounce Rate", "Traffic Sources"],
        required_permissions=["Read analytics data", "Access property"],
        data_collected=["Sessions", "Users", "Page Views", "Events", "Conversions"]
    ),
    ConnectorMetadata(
        id="zoho_books",
        name="Zoho Books",
        category="Finance",
        logo_url="/connectors/zoho.svg",
        description="Accounting for growing businesses",
        long_description="Sync Zoho Books to import invoices, expenses, and financial reports. Ideal for businesses in the Zoho ecosystem.",
        auth_type="oauth",
        supports_webhooks=True,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="hourly",
        native=True,
        beta=False,
        popularity_rank=7,
        setup_complexity="low",
        implemented=True,
        adapter_key="zoho_books",
        metrics_unlocked=["Revenue", "Expenses", "Profit Margin", "Invoice Aging"],
        required_permissions=["Read invoices", "Read expenses", "View reports"],
        data_collected=["Invoices", "Expenses", "Payments", "Contacts", "Bank Transactions"]
    ),
    ConnectorMetadata(
        id="tally",
        name="Tally Prime",
        category="ERP",
        logo_url="/connectors/tally.svg",
        description="India's leading business management software",
        long_description="Connect Tally Prime to sync vouchers, ledgers, and financial data. Perfect for Indian businesses using Tally for accounting and compliance.",
        auth_type="api_key",
        supports_webhooks=False,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="hourly",
        native=True,
        beta=False,
        popularity_rank=8,
        setup_complexity="medium",
        implemented=True,
        adapter_key="tally",
        metrics_unlocked=["Revenue", "Expenses", "Cash Balance", "Receivables", "Payables"],
        required_permissions=["Read vouchers", "Read ledgers", "Access reports"],
        data_collected=["Vouchers", "Ledgers", "Stock Items", "Groups", "Cost Centers"]
    ),
    ConnectorMetadata(
        id="razorpayx",
        name="RazorpayX",
        category="Payroll",
        logo_url="/connectors/razorpay.svg",
        description="Payroll and payouts management",
        long_description="Sync RazorpayX payroll data to track employee costs, payouts, and vendor payments. Get visibility into your burn rate and cash outflows.",
        auth_type="api_key",
        supports_webhooks=True,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="daily",
        native=True,
        beta=False,
        popularity_rank=9,
        setup_complexity="low",
        implemented=True,
        adapter_key="razorpayx",
        metrics_unlocked=["Payroll Cost", "Vendor Payments", "Burn Rate", "Employee Count"],
        required_permissions=["Read payouts", "Read contacts", "View transactions"],
        data_collected=["Payouts", "Contacts", "Fund Accounts", "Transactions"]
    ),
    ConnectorMetadata(
        id="greythr",
        name="greytHR",
        category="Payroll",
        logo_url="/connectors/greythr.svg",
        description="HR and payroll management",
        long_description="Connect greytHR to sync employee data, payroll records, and attendance. Track headcount costs and HR metrics.",
        auth_type="api_key",
        supports_webhooks=False,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="daily",
        native=True,
        beta=False,
        popularity_rank=10,
        setup_complexity="medium",
        implemented=True,
        adapter_key="greythr",
        metrics_unlocked=["Payroll Cost", "Employee Count", "Attrition Rate", "Cost per Employee"],
        required_permissions=["Read employees", "Read payroll", "Access reports"],
        data_collected=["Employees", "Payroll Records", "Attendance", "Leave Balances"]
    ),
    ConnectorMetadata(
        id="keka",
        name="Keka",
        category="Payroll",
        logo_url="/connectors/keka.svg",
        description="Modern HR and payroll platform",
        long_description="Sync Keka HR data to track employee costs, payroll, and workforce metrics. Ideal for modern Indian startups.",
        auth_type="api_key",
        supports_webhooks=False,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="daily",
        native=True,
        beta=True,
        popularity_rank=11,
        setup_complexity="medium",
        implemented=True,
        adapter_key="keka",
        metrics_unlocked=["Payroll Cost", "Employee Count", "Department Costs", "Benefits Cost"],
        required_permissions=["Read employees", "Read payroll", "View org structure"],
        data_collected=["Employees", "Payroll", "Departments", "Attendance", "Expenses"]
    ),
    ConnectorMetadata(
        id="postgresql",
        name="PostgreSQL",
        category="Databases",
        logo_url="/connectors/postgresql.svg",
        description="Connect to any PostgreSQL database",
        long_description="Directly query your PostgreSQL database to import custom metrics and data. Write SQL queries to extract exactly what you need.",
        auth_type="db_connection",
        supports_webhooks=False,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="hourly",
        native=False,
        beta=False,
        popularity_rank=12,
        setup_complexity="medium",
        implemented=True,
        metrics_unlocked=["Custom Metrics"],
        required_permissions=["Database read access"],
        data_collected=["Custom tables and views"]
    ),
    ConnectorMetadata(
        id="mysql",
        name="MySQL",
        category="Databases",
        logo_url="/connectors/mysql.svg",
        description="Connect to any MySQL database",
        long_description="Import data directly from your MySQL database using custom SQL queries. Perfect for syncing internal metrics.",
        auth_type="db_connection",
        supports_webhooks=False,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="hourly",
        native=False,
        beta=False,
        popularity_rank=13,
        setup_complexity="medium",
        implemented=False,
        metrics_unlocked=["Custom Metrics"],
        required_permissions=["Database read access"],
        data_collected=["Custom tables and views"]
    ),
    ConnectorMetadata(
        id="rest_api",
        name="REST API",
        category="Custom",
        logo_url="/connectors/api.svg",
        description="Connect to any REST API",
        long_description="Import data from any REST API by configuring endpoints, authentication, and data mapping. Flexible option for custom integrations.",
        auth_type="api_key",
        supports_webhooks=False,
        supports_polling=True,
        supports_incremental=False,
        typical_refresh="hourly",
        native=False,
        beta=True,
        popularity_rank=14,
        setup_complexity="high",
        implemented=True,
        metrics_unlocked=["Custom Metrics"],
        required_permissions=["API access"],
        data_collected=["Custom API data"]
    ),
    ConnectorMetadata(
        id="csv_upload",
        name="CSV Upload",
        category="Files",
        logo_url="/connectors/csv.svg",
        description="Upload CSV files directly",
        long_description="Manually upload CSV files to import historical data or data from systems without API access. Map columns to metrics for automatic processing.",
        auth_type="file_upload",
        supports_webhooks=False,
        supports_polling=False,
        supports_incremental=False,
        typical_refresh="manual",
        native=True,
        beta=False,
        popularity_rank=15,
        setup_complexity="low",
        implemented=True,
        metrics_unlocked=["Custom Metrics"],
        required_permissions=[],
        data_collected=["Uploaded file data"]
    ),
    ConnectorMetadata(
        id="excel_upload",
        name="Excel Upload",
        category="Files",
        logo_url="/connectors/excel.svg",
        description="Upload Excel spreadsheets",
        long_description="Import data from Excel files including multiple sheets. AI-powered column mapping helps identify metrics automatically.",
        auth_type="file_upload",
        supports_webhooks=False,
        supports_polling=False,
        supports_incremental=False,
        typical_refresh="manual",
        native=True,
        beta=False,
        popularity_rank=16,
        setup_complexity="low",
        implemented=True,
        metrics_unlocked=["Custom Metrics"],
        required_permissions=[],
        data_collected=["Uploaded spreadsheet data"]
    ),
    ConnectorMetadata(
        id="webhook",
        name="Webhook Receiver",
        category="Custom",
        logo_url="/connectors/webhook.svg",
        description="Receive data via webhooks",
        long_description="Set up a webhook endpoint to receive real-time data pushes from any system. Ideal for event-driven integrations.",
        auth_type="webhook",
        supports_webhooks=True,
        supports_polling=False,
        supports_incremental=True,
        typical_refresh="real-time",
        native=False,
        beta=True,
        popularity_rank=17,
        setup_complexity="medium",
        implemented=True,
        metrics_unlocked=["Custom Metrics"],
        required_permissions=[],
        data_collected=["Webhook event data"]
    ),
    ConnectorMetadata(
        id="google_sheets",
        name="Google Sheets",
        category="Files",
        logo_url="/connectors/google-sheets.svg",
        description="Connect to Google Sheets",
        long_description="Sync data from Google Sheets automatically. Great for teams that maintain metrics in spreadsheets.",
        auth_type="oauth",
        supports_webhooks=False,
        supports_polling=True,
        supports_incremental=False,
        typical_refresh="hourly",
        native=True,
        beta=True,
        popularity_rank=18,
        setup_complexity="low",
        implemented=False,
        metrics_unlocked=["Custom Metrics"],
        required_permissions=["Read spreadsheets"],
        data_collected=["Spreadsheet data"]
    ),
    ConnectorMetadata(
        id="shopify",
        name="Shopify",
        category="Finance",
        logo_url="/connectors/shopify.svg",
        description="E-commerce platform",
        long_description="Sync Shopify orders, products, and customer data. Track GMV, order volume, and e-commerce metrics.",
        auth_type="oauth",
        supports_webhooks=True,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="real-time",
        native=True,
        beta=True,
        popularity_rank=19,
        setup_complexity="low",
        implemented=False,
        metrics_unlocked=["GMV", "Order Count", "AOV", "Customer Count", "Refund Rate"],
        required_permissions=["Read orders", "Read products", "Read customers"],
        data_collected=["Orders", "Products", "Customers", "Refunds", "Inventory"]
    ),
    ConnectorMetadata(
        id="mixpanel",
        name="Mixpanel",
        category="Analytics",
        logo_url="/connectors/mixpanel.svg",
        description="Product analytics platform",
        long_description="Import Mixpanel event data to understand user behavior, feature adoption, and retention. Combine with revenue data for LTV analysis.",
        auth_type="api_key",
        supports_webhooks=False,
        supports_polling=True,
        supports_incremental=True,
        typical_refresh="daily",
        native=True,
        beta=True,
        popularity_rank=20,
        setup_complexity="medium",
        implemented=False,
        metrics_unlocked=["DAU", "MAU", "Retention", "Feature Adoption", "Conversion Funnel"],
        required_permissions=["Read events", "Read user data"],
        data_collected=["Events", "User Profiles", "Cohorts", "Funnels"]
    ),
]

@router.get("/catalog", response_model=List[CatalogConnector])
async def get_connector_catalog(
    category: Optional[str] = None,
    native_only: Optional[bool] = None,
    implemented_only: Optional[bool] = None,
    company_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get the full connector catalog with installation status.
    This is the single source of truth for the marketplace UI.
    """
    connectors = CONNECTOR_REGISTRY.copy()
    
    if category:
        connectors = [c for c in connectors if c.category.lower() == category.lower()]
    
    if native_only:
        connectors = [c for c in connectors if c.native]
    
    if implemented_only:
        connectors = [c for c in connectors if c.implemented]
    
    connectors.sort(key=lambda x: x.popularity_rank)
    
    company_connectors = {}
    if company_id:
        from server.models.company import Company
        try:
            company = db.query(Company).filter(Company.id == company_id).first()
            if company and company.metadata_json:
                company_connectors = company.metadata_json.get("connectors", {})
        except Exception:
            pass
    
    result = []
    for connector in connectors:
        status = None
        conn_meta = company_connectors.get(connector.id)
        if conn_meta and conn_meta.get("connected"):
            status = ConnectorStatus(
                connector_id=connector.id,
                status="active",
                last_sync=conn_meta.get("last_sync"),
                record_count=conn_meta.get("records_synced", 0),
                error_summary=conn_meta.get("last_error"),
            )
        catalog_connector = CatalogConnector(
            **connector.model_dump(),
            install_status=status
        )
        result.append(catalog_connector)
    
    return result

@router.get("/catalog/{connector_id}", response_model=CatalogConnector)
async def get_connector_detail(
    connector_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific connector.
    """
    connector = next((c for c in CONNECTOR_REGISTRY if c.id == connector_id), None)
    
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found")
    
    return CatalogConnector(
        **connector.model_dump(),
        install_status=None
    )

@router.get("/categories")
async def get_categories():
    """Get all available categories with counts."""
    categories = {}
    for connector in CONNECTOR_REGISTRY:
        cat = connector.category
        if cat not in categories:
            categories[cat] = {"name": cat, "count": 0}
        categories[cat]["count"] += 1
    
    return list(categories.values())
