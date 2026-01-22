# Copilot V3: Enterprise Privacy & Evaluation System

## Overview

Copilot V3 introduces enterprise-grade privacy controls and quality assurance capabilities through:

1. **PII Redaction System** - Automatic detection and redaction of sensitive data before LLM calls
2. **Enterprise Audit Logging** - Complete audit trail of all OpenAI API interactions
3. **Golden Dataset Tests** - Reference test cases for regression testing
4. **Eval Harness** - Automated scoring for quality metrics

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Request                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PII Redactor Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Email      │  │   Phone      │  │   Credit Card        │   │
│  │   Patterns   │  │   Patterns   │  │   (Luhn Validated)   │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   SSN/NIN    │  │   IBAN/Bank  │  │   API Keys/Tokens    │   │
│  │   Patterns   │  │   Account    │  │   Patterns           │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Audited OpenAI Client                           │
│  • Logs all API calls to llm_audit_logs table                   │
│  • Tracks token usage (input/output)                             │
│  • Records latency metrics                                       │
│  • Stores prompt hash for deduplication                          │
│  • Captures PII findings metadata                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OpenAI API                                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Eval Harness (Post-hoc)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Citation    │  │  Structure   │  │   Hallucination      │   │
│  │  Coverage    │  │  Compliance  │  │   Risk Score         │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐                                               │
│  │  PII Leak    │                                               │
│  │  Detection   │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

## 1. PII Redaction System

### Location
`server/lib/privacy/pii_redactor.py`

### Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `off` | No redaction | Development/testing |
| `standard` | Basic PII types | Default for most users |
| `strict` | Extended patterns + names | Enterprise/regulated industries |

### Detected PII Types

#### Standard Mode
- Email addresses
- Phone numbers (US, international formats)
- Credit card numbers (Luhn-validated)
- SSN/National ID numbers
- IBAN/Bank account numbers
- API keys and tokens
- URLs with credentials

#### Strict Mode (Additional)
- Personal names (common patterns)
- Addresses
- Dates of birth
- IP addresses
- Passport numbers

### Credit Card Validation

The system uses the Luhn algorithm to validate credit card numbers, reducing false positives:

```python
def luhn_checksum(card_number: str) -> bool:
    digits = [int(d) for d in card_number if d.isdigit()]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(divmod(d * 2, 10))
    return checksum % 10 == 0
```

### Usage in Code

```python
from server.lib.privacy.pii_redactor import PIIRedactor

redactor = PIIRedactor(mode="standard")
result = redactor.redact("Contact john@example.com for details")

print(result.redacted_text)  # "Contact [EMAIL_REDACTED] for details"
print(result.findings)  # [{"type": "email", "count": 1, "confidence": "high"}]
```

## 2. Enterprise Audit Logging

### Database Schema

```sql
CREATE TABLE llm_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id INTEGER REFERENCES companies(id),
    user_id INTEGER REFERENCES users(id),
    endpoint VARCHAR(100) NOT NULL,
    model VARCHAR(50) NOT NULL,
    pii_mode VARCHAR(20) NOT NULL,
    prompt_hash VARCHAR(64) NOT NULL,
    input_chars_original INTEGER NOT NULL,
    input_chars_redacted INTEGER NOT NULL,
    pii_findings_json JSONB,
    redacted_prompt_preview TEXT,
    redacted_output_preview TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Audited Client Usage

```python
from server.lib.llm.openai_client import get_audited_client

async with get_audited_client(
    db=db_session,
    company_id=company.id,
    user_id=user.id,
    pii_mode="standard"
) as client:
    response = await client.chat_completion(
        messages=[{"role": "user", "content": "Analyze my financials"}],
        model="gpt-4o"
    )
```

### Admin Dashboard

Access at `/admin/llm-audit` to view:
- Total requests over time
- Token consumption metrics
- Average latency
- PII detection statistics
- Filterable log entries with detailed view

## 3. Golden Dataset Tests

### Location
`server/lib/evals/golden_datasets.py`

### Categories

| Category | Description | Test Count |
|----------|-------------|------------|
| `cfo_analysis` | CFO agent financial calculations | 3 |
| `market_analysis` | Market agent competitor/ICP research | 2 |
| `strategy_analysis` | Strategy agent GTM planning | 2 |
| `pii_redaction` | PII detection accuracy | 3 |
| `extraction_accuracy` | Document metric extraction | 2 |

### Test Case Structure

```python
{
    "id": "cfo_001",
    "name": "Basic Runway Calculation",
    "description": "Test CFO agent's ability to calculate runway",
    "category": "cfo_analysis",
    "input": {
        "user_message": "What is our current runway?",
        "company_context": {
            "cash_balance": 500000,
            "monthly_burn": 42000
        }
    },
    "expected": {
        "must_contain_insights": ["runway_months", "burn_rate"],
        "structure_requirements": ["findings", "assumptions"],
        "numerical_accuracy": {
            "runway_months": {"min": 14, "max": 18}
        }
    },
    "scoring_weights": {
        "numerical_accuracy": 0.4,
        "structure_compliance": 0.3,
        "insight_coverage": 0.3
    }
}
```

## 4. Eval Harness

### Location
`server/lib/evals/eval_runner.py`

### Evaluation Suites

#### copilot_quality
Measures overall response quality:
- **Citation Coverage** (25%): Presence and validity of source citations
- **Structure Compliance** (25%): Required sections present
- **Hallucination Risk** (25%): Confidence language usage
- **PII Leak Check** (25%): No leaked PII in output

#### extraction_accuracy
Measures document extraction quality:
- **Field Coverage**: All expected fields extracted
- **Value Accuracy**: Numerical precision
- **Format Handling**: Correct unit/currency parsing

#### pii_redaction
Measures PII detection accuracy:
- **Detection Rate**: Correctly identified PII
- **False Positive Rate**: Non-PII incorrectly flagged
- **Luhn Validation**: Credit card validation accuracy

### Scoring Functions

```python
def score_citation_coverage(response: str, sources: List[str]) -> EvalScore:
    """
    Scores: 1.0 if citations match sources, 0.0 if no citations
    Partial scores for incomplete coverage
    """

def score_structure_compliance(response: dict, required_fields: List[str]) -> EvalScore:
    """
    Scores based on presence of required fields:
    - findings, assumptions, risks, recommendations, next_questions
    """

def score_hallucination_risk(response: str) -> EvalScore:
    """
    Lower score = higher risk
    Checks for: hedge words, confidence qualifiers, cited claims
    """

def score_pii_leak_check(response: str, pii_mode: str) -> EvalScore:
    """
    Scores 1.0 if no PII patterns found in output
    Scores 0.0 if any PII detected
    """
```

### Running Evaluations

Via Admin UI:
1. Navigate to `/admin/evals`
2. Select evaluation suite
3. Click "Run Evaluation"
4. View results with metric breakdown

Via API:
```bash
POST /api/admin/evals/run
{
    "suite_name": "copilot_quality",
    "inputs": { ... }
}
```

## API Endpoints

### LLM Audit

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/llm-audit` | GET | List audit logs (paginated) |
| `/api/admin/llm-audit/stats/summary` | GET | Aggregated statistics |

### Evaluations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/evals/suites` | GET | List available suites |
| `/api/admin/evals/runs` | GET | List eval runs (paginated) |
| `/api/admin/evals/run` | POST | Start new evaluation |

## Configuration

### Environment Variables

```bash
# PII default mode (off|standard|strict)
PII_DEFAULT_MODE=standard

# Audit log retention days
AUDIT_LOG_RETENTION_DAYS=90

# Enable/disable audit logging
AUDIT_LOGGING_ENABLED=true
```

### Per-Company Settings

Companies can override PII mode via company settings:
```json
{
    "privacy": {
        "pii_mode": "strict",
        "audit_enabled": true
    }
}
```

## Security Considerations

1. **Data Minimization**: Only redacted previews stored in audit logs
2. **Prompt Hashing**: SHA-256 hash for deduplication without storing full prompts
3. **Access Control**: Admin-only access to audit logs and eval results
4. **PII Findings**: Only type/count stored, not actual values

## Future Enhancements

- [ ] Custom PII patterns per company
- [ ] Real-time PII detection alerts
- [ ] Automated eval scheduling (daily/weekly)
- [ ] Eval result trending and regression alerts
- [ ] Export audit logs to SIEM systems
- [ ] SOC 2 compliance report generation
