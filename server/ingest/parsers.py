import pandas as pd
from io import StringIO
from typing import List, Dict, Any
from datetime import datetime

def parse_csv(content: str) -> pd.DataFrame:
    return pd.read_csv(StringIO(content))

def detect_column_mapping(df: pd.DataFrame, dataset_type: str) -> Dict[str, str]:
    columns = [c.lower().strip() for c in df.columns]
    mapping = {}
    
    if dataset_type == "financial":
        field_patterns = {
            "period_start": ["period_start", "start_date", "date_start", "from", "period start"],
            "period_end": ["period_end", "end_date", "date_end", "to", "period end"],
            "revenue": ["revenue", "total_revenue", "sales", "income"],
            "cogs": ["cogs", "cost_of_goods", "cost_of_sales", "direct_costs"],
            "opex": ["opex", "operating_expenses", "operating_costs", "overhead"],
            "payroll": ["payroll", "salaries", "wages", "compensation", "personnel"],
            "other_costs": ["other_costs", "other_expenses", "misc_costs", "other"],
            "cash_balance": ["cash_balance", "cash", "bank_balance", "ending_cash"],
        }
    elif dataset_type == "transactions":
        field_patterns = {
            "txn_date": ["txn_date", "date", "transaction_date", "order_date"],
            "customer_id": ["customer_id", "customer", "client_id", "account_id"],
            "product": ["product", "product_name", "item", "sku"],
            "amount": ["amount", "total", "revenue", "price", "value"],
            "cost": ["cost", "cogs", "expense"],
            "channel": ["channel", "source", "sales_channel"],
        }
    elif dataset_type == "customers":
        field_patterns = {
            "customer_id": ["customer_id", "customer", "id", "account_id"],
            "segment": ["segment", "tier", "category", "type"],
            "signup_date": ["signup_date", "created_date", "joined", "registration_date"],
            "region": ["region", "country", "location", "geography"],
            "plan": ["plan", "subscription", "plan_type", "pricing_tier"],
        }
    else:
        return mapping
    
    for field, patterns in field_patterns.items():
        for i, col in enumerate(columns):
            if any(p in col for p in patterns):
                mapping[field] = df.columns[i]
                break
    
    return mapping

def parse_financial_records(df: pd.DataFrame, mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    records = []
    for _, row in df.iterrows():
        record = {
            "period_start": pd.to_datetime(row.get(mapping.get("period_start", ""), None)),
            "period_end": pd.to_datetime(row.get(mapping.get("period_end", ""), None)),
            "revenue": float(row.get(mapping.get("revenue", ""), 0) or 0),
            "cogs": float(row.get(mapping.get("cogs", ""), 0) or 0),
            "opex": float(row.get(mapping.get("opex", ""), 0) or 0),
            "payroll": float(row.get(mapping.get("payroll", ""), 0) or 0),
            "other_costs": float(row.get(mapping.get("other_costs", ""), 0) or 0),
            "cash_balance": float(row.get(mapping.get("cash_balance", ""), 0) or 0),
        }
        records.append(record)
    return records

def parse_transaction_records(df: pd.DataFrame, mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    records = []
    for _, row in df.iterrows():
        record = {
            "txn_date": pd.to_datetime(row.get(mapping.get("txn_date", ""), None)),
            "customer_id": str(row.get(mapping.get("customer_id", ""), "") or ""),
            "product": str(row.get(mapping.get("product", ""), "") or ""),
            "amount": float(row.get(mapping.get("amount", ""), 0) or 0),
            "cost": float(row.get(mapping.get("cost", ""), 0) or 0),
            "channel": str(row.get(mapping.get("channel", ""), "") or ""),
        }
        records.append(record)
    return records

def parse_customer_records(df: pd.DataFrame, mapping: Dict[str, str]) -> List[Dict[str, Any]]:
    records = []
    for _, row in df.iterrows():
        record = {
            "customer_id": str(row.get(mapping.get("customer_id", ""), "") or ""),
            "segment": str(row.get(mapping.get("segment", ""), "") or ""),
            "signup_date": pd.to_datetime(row.get(mapping.get("signup_date", ""), None)),
            "region": str(row.get(mapping.get("region", ""), "") or ""),
            "plan": str(row.get(mapping.get("plan", ""), "") or ""),
        }
        records.append(record)
    return records
