"""
Built-in metric templates for common SaaS metrics.
"""

REVENUE_TEMPLATE = """
meta:
  id: revenue
  name: Revenue
  description: Total revenue from all paid transactions
  unit: USD
  grain: monthly
  tags: [financial, core]
  version: 1
  status: certified

dependencies:
  - data_source_type: stripe
    event_type: invoice.paid
    required: true

inputs:
  time_range:
    lookback_days: 365

mapping:
  fields:
    amount: "$.amount"
    currency: "$.currency"
    status: "$.status"

logic:
  type: aggregate
  source: raw_events
  measures:
    - name: value
      agg: sum
      field: amount
      where:
        - field: status
          op: "="
          value: paid

  dimensions:
    - name: time_bucket
      expr: "time_bucket(monthly, occurred_at)"

postprocess:
  - op: scale
    factor: 0.01
  - op: clamp
    min: 0

output:
  primary_value: value
  time_bucket: time_bucket
"""

MRR_TEMPLATE = """
meta:
  id: mrr
  name: Monthly Recurring Revenue
  description: Sum of all active recurring subscription amounts
  unit: USD
  grain: monthly
  tags: [financial, recurring, core]
  version: 1
  status: certified

dependencies:
  - data_source_type: stripe
    event_type: subscription.updated
    required: true

mapping:
  fields:
    amount: "$.plan.amount"
    status: "$.status"
    interval: "$.plan.interval"

logic:
  type: aggregate
  source: raw_events
  measures:
    - name: value
      agg: sum
      field: amount
      where:
        - field: status
          op: "="
          value: active
        - field: interval
          op: "="
          value: month

  dimensions:
    - name: time_bucket
      expr: "time_bucket(monthly, occurred_at)"

postprocess:
  - op: scale
    factor: 0.01
  - op: clamp
    min: 0
"""

ARR_TEMPLATE = """
meta:
  id: arr
  name: Annual Recurring Revenue
  description: MRR multiplied by 12
  unit: USD
  grain: monthly
  tags: [financial, recurring, core]
  version: 1
  status: certified

dependencies: []

logic:
  type: compose
  metrics:
    - metric_id: mrr
      alias: mrr
  expression: "mrr * 12"
"""

BURN_TEMPLATE = """
meta:
  id: burn_rate
  name: Burn Rate
  description: Total monthly expenses and costs
  unit: USD
  grain: monthly
  tags: [financial, core]
  version: 1
  status: certified

dependencies:
  - data_source_type: quickbooks
    required: true

mapping:
  fields:
    amount: "$.amount"
    type: "$.type"
    category: "$.account_category"

logic:
  type: aggregate
  source: raw_events
  measures:
    - name: value
      agg: sum
      field: amount
      where:
        - field: type
          op: "="
          value: expense

  dimensions:
    - name: time_bucket
      expr: "time_bucket(monthly, occurred_at)"

postprocess:
  - op: abs
  - op: clamp
    min: 0
"""

RUNWAY_TEMPLATE = """
meta:
  id: runway
  name: Runway
  description: Months of cash remaining at current burn rate
  unit: days
  grain: monthly
  tags: [financial, core, health]
  version: 1
  status: draft

dependencies: []

logic:
  type: compose
  metrics:
    - metric_id: cash_balance
      alias: cash
    - metric_id: burn_rate
      alias: burn
  expression: "cash / burn if burn > 0 else 999"
"""

CAC_TEMPLATE = """
meta:
  id: cac
  name: Customer Acquisition Cost
  description: Total ad spend divided by new customers acquired
  unit: USD
  grain: monthly
  tags: [marketing, growth]
  version: 1
  status: draft

dependencies:
  - data_source_type: google_ads
    required: false
  - data_source_type: facebook_ads
    required: false

logic:
  type: compose
  metrics:
    - metric_id: ad_spend
      alias: spend
    - metric_id: new_customers
      alias: customers
  expression: "spend / customers if customers > 0 else 0"
"""

LTV_TEMPLATE = """
meta:
  id: ltv
  name: Customer Lifetime Value
  description: Average revenue per user multiplied by gross margin divided by churn
  unit: USD
  grain: monthly
  tags: [financial, growth]
  version: 1
  status: draft

dependencies: []

logic:
  type: compose
  metrics:
    - metric_id: arpu
      alias: arpu
    - metric_id: gross_margin
      alias: margin
    - metric_id: churn_rate
      alias: churn
  expression: "(arpu * margin) / churn if churn > 0 else arpu * margin * 24"
"""

CHURN_TEMPLATE = """
meta:
  id: churn_rate
  name: Churn Rate
  description: Percentage of customers lost in the period
  unit: "%"
  grain: monthly
  tags: [growth, health]
  version: 1
  status: certified

dependencies:
  - data_source_type: stripe
    event_type: subscription.deleted
    required: true

mapping:
  fields:
    customer_id: "$.customer"
    canceled_at: "$.canceled_at"

logic:
  type: aggregate
  source: raw_events
  measures:
    - name: churned
      agg: count
      field: "*"
    - name: total
      agg: count
      field: "*"

  dimensions:
    - name: time_bucket
      expr: "time_bucket(monthly, occurred_at)"

postprocess:
  - op: scale
    factor: 100
"""

GROSS_MARGIN_TEMPLATE = """
meta:
  id: gross_margin
  name: Gross Margin
  description: (Revenue - COGS) / Revenue as a percentage
  unit: "%"
  grain: monthly
  tags: [financial, profitability]
  version: 1
  status: draft

dependencies: []

logic:
  type: compose
  metrics:
    - metric_id: revenue
      alias: revenue
    - metric_id: cogs
      alias: cogs
  expression: "((revenue - cogs) / revenue) * 100 if revenue > 0 else 0"
"""

NRR_TEMPLATE = """
meta:
  id: nrr
  name: Net Revenue Retention
  description: (Starting ARR + Expansions - Contractions - Churn) / Starting ARR
  unit: "%"
  grain: monthly
  tags: [growth, retention]
  version: 1
  status: draft

dependencies: []

logic:
  type: compose
  metrics:
    - metric_id: starting_arr
      alias: start
    - metric_id: expansion_arr
      alias: expansion
    - metric_id: contraction_arr
      alias: contraction
    - metric_id: churned_arr
      alias: churned
  expression: "((start + expansion - contraction - churned) / start) * 100 if start > 0 else 100"
"""

SYSTEM_METRIC_TEMPLATES = [
    {
        "key": "revenue",
        "name": "Revenue",
        "description": "Total revenue from all paid transactions",
        "definition": REVENUE_TEMPLATE,
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["financial", "core"],
        "dependencies": [{"data_source_type": "stripe", "event_type": "invoice.paid"}],
    },
    {
        "key": "mrr",
        "name": "Monthly Recurring Revenue",
        "description": "Sum of all active recurring subscription amounts",
        "definition": MRR_TEMPLATE,
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["financial", "recurring", "core"],
        "dependencies": [{"data_source_type": "stripe"}],
    },
    {
        "key": "arr",
        "name": "Annual Recurring Revenue",
        "description": "MRR multiplied by 12",
        "definition": ARR_TEMPLATE,
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["financial", "recurring", "core"],
        "dependencies": [],
    },
    {
        "key": "burn_rate",
        "name": "Burn Rate",
        "description": "Total monthly expenses and costs",
        "definition": BURN_TEMPLATE,
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["financial", "core"],
        "dependencies": [{"data_source_type": "quickbooks"}],
    },
    {
        "key": "runway",
        "name": "Runway",
        "description": "Months of cash remaining at current burn rate",
        "formula": "cash_balance / burn_rate",
        "unit": "months",
        "format_type": "number",
        "grain": "monthly",
        "tags": ["financial", "core", "health"],
    },
    {
        "key": "churn_rate",
        "name": "Churn Rate",
        "description": "Percentage of customers lost in the period",
        "definition": CHURN_TEMPLATE,
        "unit": "%",
        "format_type": "percentage",
        "grain": "monthly",
        "tags": ["growth", "health"],
        "dependencies": [{"data_source_type": "stripe"}],
    },
    {
        "key": "gross_margin",
        "name": "Gross Margin",
        "description": "(Revenue - COGS) / Revenue as a percentage",
        "formula": "(revenue - cogs) / revenue * 100",
        "unit": "%",
        "format_type": "percentage",
        "grain": "monthly",
        "tags": ["financial", "profitability"],
    },
    {
        "key": "customer_count",
        "name": "Customer Count",
        "description": "Total number of active customers",
        "formula": "count()",
        "format_type": "number",
        "grain": "monthly",
        "tags": ["growth"],
    },
    {
        "key": "avg_transaction",
        "name": "Average Transaction Value",
        "description": "Average value per transaction",
        "formula": "avg(amount)",
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["financial"],
    },
    {
        "key": "total_revenue",
        "name": "Total Revenue",
        "description": "Total revenue including one-time and recurring",
        "formula": "sum(amount)",
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["financial", "core"],
    },
    {
        "key": "cash_balance",
        "name": "Cash Balance",
        "description": "Total cash on hand",
        "formula": "cash_balance",
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["financial", "core"],
    },
    {
        "key": "net_burn",
        "name": "Net Burn",
        "description": "Net cash burn per month (costs minus revenue)",
        "formula": "total_costs - revenue",
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["financial", "core"],
    },
    {
        "key": "cac",
        "name": "Customer Acquisition Cost",
        "description": "Cost to acquire a new customer",
        "definition": CAC_TEMPLATE,
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["marketing", "growth"],
    },
    {
        "key": "ltv",
        "name": "Customer Lifetime Value",
        "description": "Expected total revenue from a customer over their lifetime",
        "definition": LTV_TEMPLATE,
        "unit": "USD",
        "format_type": "currency",
        "grain": "monthly",
        "tags": ["financial", "growth"],
    },
    {
        "key": "ltv_cac_ratio",
        "name": "LTV/CAC Ratio",
        "description": "Lifetime value divided by acquisition cost",
        "formula": "ltv / cac",
        "format_type": "number",
        "grain": "monthly",
        "tags": ["financial", "growth", "health"],
    },
    {
        "key": "headcount",
        "name": "Headcount",
        "description": "Total number of employees",
        "formula": "headcount",
        "format_type": "number",
        "grain": "monthly",
        "tags": ["operations"],
    },
]
