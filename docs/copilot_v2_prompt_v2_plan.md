# Copilot V2+ (Prompt v2) Implementation Plan

## Overview
Implementing enhanced Copilot features focused on:
1. Truth-first citations (PDF + Web)
2. Data Health score
3. Operating Cadence + Alerts/Reminders
4. Driver-based Forecast scaffolding

## Current Architecture

### Frontend
- `client/src/pages/copilot.tsx` - Main Copilot UI with chat interface
- `client/src/pages/alerts.tsx` - Existing alerts page
- `client/src/pages/scenarios.tsx` - Scenario planning

### Backend
- `server/api/copilot.py` - Chat API, CKB endpoints, memo export
- `server/copilot/agents/` - CFO, Market, Strategy agents
- `server/copilot/ckb_storage.py` - Company Knowledge Base persistence
- `server/models/company_decision.py` - Decision/Scenario models

### Database
- PostgreSQL with SQLAlchemy ORM
- Existing tables: companies, truth_scans, scenarios, company_decisions, company_scenarios

## New Tables

### 1. company_sources (Citations)
```python
class CompanySource(Base):
    __tablename__ = "company_sources"
    id = Column(UUID, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    kind = Column(String)  # "pdf" | "web" | "manual"
    title = Column(Text)
    url = Column(Text, nullable=True)
    doc_id = Column(Text, nullable=True)
    page = Column(Integer, nullable=True)
    table_id = Column(Text, nullable=True)
    row_ref = Column(Text, nullable=True)
    cell_ref = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 2. company_workstreams (Operating Cadence)
```python
class CompanyWorkstream(Base):
    __tablename__ = "company_workstreams"
    id = Column(UUID, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    name = Column(String)
    cadence = Column(String)  # "weekly" | "monthly" | "quarterly"
    enabled = Column(Boolean, default=True)
    config_json = Column(JSON, default={})
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

### 3. company_alerts (Alerts/Reminders)
```python
class CompanyAlert(Base):
    __tablename__ = "company_alerts"
    id = Column(UUID, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    type = Column(String)  # "runway_drop" | "cac_spike" | "revenue_miss" | "churn_spike" | "custom"
    severity = Column(String)  # "high" | "medium" | "low"
    message = Column(Text)
    rule_json = Column(JSON)
    triggered_at = Column(DateTime)
    resolved_at = Column(DateTime, nullable=True)
    status = Column(String, default="open")  # "open" | "resolved" | "snoozed"
```

### 4. company_driver_models (Forecasting)
```python
class CompanyDriverModel(Base):
    __tablename__ = "company_driver_models"
    id = Column(UUID, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    model_name = Column(String)
    template = Column(String)  # "saas" | "marketplace" | "services"
    drivers_json = Column(JSON)
    assumptions_json = Column(JSON)
    outputs_json = Column(JSON)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

## New API Endpoints

### Citations
- Response structure enhanced with `citations` and `highlighted_claims`

### Data Health
- `GET /companies/:companyId/data-health` - Returns score, grade, issues, coverage

### Workstreams
- `GET /companies/:companyId/workstreams`
- `POST /companies/:companyId/workstreams`
- `PATCH /companies/:companyId/workstreams/:id`

### Alerts
- `GET /companies/:companyId/alerts?status=open`
- `POST /companies/:companyId/alerts/evaluate`

### Driver Models
- `POST /companies/:companyId/driver-models`
- `POST /companies/:companyId/driver-models/:id/run`
- `GET /companies/:companyId/driver-models`

## Files to Edit

### Backend
- `server/models/company_source.py` (new)
- `server/models/company_workstream.py` (new)
- `server/models/company_alert.py` (new)
- `server/models/company_driver_model.py` (new)
- `server/api/copilot.py` - Add citations, data health
- `server/api/workstreams.py` (new)
- `server/api/alerts.py` (new)
- `server/api/driver_models.py` (new)
- `server/core/migrations.py` - Add new table migrations

### Frontend
- `client/src/pages/copilot.tsx` - Citations toggle, Data Health widget
- `client/src/pages/alerts.tsx` - Enhanced alerts display
- `client/src/pages/scenarios.tsx` - Driver-based forecasting section

## Testing Checklist

1. [ ] Migrations run successfully
2. [ ] Data Health endpoint returns score and issues
3. [ ] Citations toggle in Copilot UI works
4. [ ] Workstreams CRUD operations work
5. [ ] Alert evaluation triggers on low runway
6. [ ] Driver model forecast runs correctly
7. [ ] No console errors, TypeScript types pass

## Implementation Order

1. Database models and migrations
2. Data Health endpoint and UI widget
3. Citations response structure
4. Workstreams and Alerts
5. Driver-based forecasting
6. Router prompt updates for special modes
