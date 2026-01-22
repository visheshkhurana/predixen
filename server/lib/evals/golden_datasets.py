"""
Golden Dataset Tests for Copilot V3 Quality Assurance

This module provides reference test cases for evaluating the quality of
Copilot responses across different scenarios. Each golden dataset includes:
- Input prompts (user messages with company context)
- Expected outputs (structure, citations, key insights)
- Scoring criteria for regression testing

Usage:
    from server.lib.evals.golden_datasets import GOLDEN_DATASETS
    for dataset in GOLDEN_DATASETS:
        result = run_eval(dataset["input"])
        score = compare_against_expected(result, dataset["expected"])
"""

from typing import TypedDict, List, Dict, Any, Optional

class GoldenTestCase(TypedDict):
    id: str
    name: str
    description: str
    category: str
    input: Dict[str, Any]
    expected: Dict[str, Any]
    scoring_weights: Dict[str, float]

CFO_ANALYSIS_TESTS: List[GoldenTestCase] = [
    {
        "id": "cfo_001",
        "name": "Basic Runway Calculation",
        "description": "Test CFO agent's ability to calculate runway from P&L data",
        "category": "cfo_analysis",
        "input": {
            "user_message": "What is our current runway?",
            "company_context": {
                "cash_balance": 500000,
                "monthly_burn": 42000,
                "monthly_revenue": 12000,
                "industry": "saas"
            }
        },
        "expected": {
            "must_contain_insights": [
                "runway_months",
                "burn_rate",
                "cash_balance"
            ],
            "structure_requirements": [
                "findings",
                "assumptions", 
                "recommendations"
            ],
            "numerical_accuracy": {
                "runway_months": {"min": 14, "max": 18},
                "net_burn": {"min": 28000, "max": 32000}
            }
        },
        "scoring_weights": {
            "numerical_accuracy": 0.4,
            "structure_compliance": 0.3,
            "insight_coverage": 0.3
        }
    },
    {
        "id": "cfo_002", 
        "name": "Currency Conversion (INR)",
        "description": "Test CFO agent's FX conversion capabilities",
        "category": "cfo_analysis",
        "input": {
            "user_message": "Convert our financials to INR",
            "company_context": {
                "cash_balance": 100000,
                "monthly_burn": 25000,
                "currency": "USD"
            }
        },
        "expected": {
            "must_contain_insights": [
                "converted_cash",
                "converted_burn",
                "exchange_rate"
            ],
            "structure_requirements": [
                "findings",
                "assumptions"
            ]
        },
        "scoring_weights": {
            "fx_conversion_present": 0.5,
            "structure_compliance": 0.3,
            "insight_coverage": 0.2
        }
    },
    {
        "id": "cfo_003",
        "name": "Unit Economics Analysis",
        "description": "Test CFO agent's unit economics calculations",
        "category": "cfo_analysis",
        "input": {
            "user_message": "Analyze our unit economics - is our CAC sustainable?",
            "company_context": {
                "cac": 450,
                "ltv": 1200,
                "monthly_churn": 0.05,
                "arpu": 99,
                "industry": "saas"
            }
        },
        "expected": {
            "must_contain_insights": [
                "ltv_cac_ratio",
                "payback_period",
                "churn_impact"
            ],
            "structure_requirements": [
                "findings",
                "assumptions",
                "risks"
            ],
            "numerical_accuracy": {
                "ltv_cac_ratio": {"min": 2.5, "max": 2.8}
            }
        },
        "scoring_weights": {
            "numerical_accuracy": 0.4,
            "structure_compliance": 0.3,
            "insight_coverage": 0.3
        }
    }
]

MARKET_ANALYSIS_TESTS: List[GoldenTestCase] = [
    {
        "id": "market_001",
        "name": "Competitor Analysis",
        "description": "Test Market agent's competitor research capabilities",
        "category": "market_analysis",
        "input": {
            "user_message": "Who are our main competitors in the B2B SaaS analytics space?",
            "company_context": {
                "industry": "saas",
                "vertical": "analytics",
                "target_market": "b2b"
            }
        },
        "expected": {
            "must_contain_insights": [
                "competitor_list",
                "market_positioning",
                "competitive_advantages"
            ],
            "structure_requirements": [
                "findings",
                "next_questions"
            ]
        },
        "scoring_weights": {
            "insight_coverage": 0.5,
            "structure_compliance": 0.3,
            "citation_coverage": 0.2
        }
    },
    {
        "id": "market_002",
        "name": "ICP Definition",
        "description": "Test Market agent's ICP definition capabilities",
        "category": "market_analysis",
        "input": {
            "user_message": "Help me define our ideal customer profile",
            "company_context": {
                "industry": "fintech",
                "product_type": "payment_processing",
                "current_customers": ["smb", "mid_market"]
            }
        },
        "expected": {
            "must_contain_insights": [
                "company_size",
                "industry_focus",
                "pain_points",
                "buying_triggers"
            ],
            "structure_requirements": [
                "findings",
                "assumptions",
                "next_questions"
            ]
        },
        "scoring_weights": {
            "insight_coverage": 0.5,
            "structure_compliance": 0.3,
            "actionability": 0.2
        }
    }
]

STRATEGY_ANALYSIS_TESTS: List[GoldenTestCase] = [
    {
        "id": "strategy_001",
        "name": "GTM Strategy Planning",
        "description": "Test Strategy agent's GTM planning capabilities",
        "category": "strategy_analysis",
        "input": {
            "user_message": "Help me plan our go-to-market strategy for the next quarter",
            "company_context": {
                "stage": "seed",
                "product_status": "launched",
                "target_market": "smb",
                "current_mrr": 15000
            }
        },
        "expected": {
            "must_contain_insights": [
                "channels",
                "messaging",
                "metrics",
                "timeline"
            ],
            "structure_requirements": [
                "findings",
                "recommendations",
                "risks"
            ]
        },
        "scoring_weights": {
            "actionability": 0.4,
            "structure_compliance": 0.3,
            "insight_coverage": 0.3
        }
    },
    {
        "id": "strategy_002",
        "name": "30/60/90 Day Execution Plan",
        "description": "Test Strategy agent's execution planning",
        "category": "strategy_analysis",
        "input": {
            "user_message": "Create a 30/60/90 day plan for increasing our MRR",
            "company_context": {
                "current_mrr": 25000,
                "target_mrr": 50000,
                "team_size": 5,
                "main_channel": "outbound"
            }
        },
        "expected": {
            "must_contain_insights": [
                "30_day_goals",
                "60_day_goals", 
                "90_day_goals",
                "milestones",
                "kpis"
            ],
            "structure_requirements": [
                "findings",
                "recommendations",
                "assumptions"
            ]
        },
        "scoring_weights": {
            "timeline_clarity": 0.3,
            "actionability": 0.3,
            "structure_compliance": 0.2,
            "insight_coverage": 0.2
        }
    }
]

PII_REDACTION_TESTS: List[GoldenTestCase] = [
    {
        "id": "pii_001",
        "name": "Email Redaction",
        "description": "Test PII redactor's email detection",
        "category": "pii_redaction",
        "input": {
            "text": "Contact john.doe@company.com or jane@startup.io for details",
            "mode": "standard"
        },
        "expected": {
            "redacted_count": 2,
            "pii_types": ["email"],
            "must_redact": ["john.doe@company.com", "jane@startup.io"],
            "output_contains": ["[EMAIL_REDACTED]"]
        },
        "scoring_weights": {
            "detection_accuracy": 0.5,
            "redaction_completeness": 0.5
        }
    },
    {
        "id": "pii_002",
        "name": "Credit Card Redaction (Luhn)",
        "description": "Test PII redactor's credit card detection with Luhn validation",
        "category": "pii_redaction",
        "input": {
            "text": "Card number 4111111111111111 expires 12/25. Invalid: 1234567890123456",
            "mode": "standard"
        },
        "expected": {
            "redacted_count": 1,
            "pii_types": ["credit_card"],
            "must_redact": ["4111111111111111"],
            "must_not_redact": ["1234567890123456"],
            "output_contains": ["[CARD_REDACTED]"]
        },
        "scoring_weights": {
            "luhn_validation": 0.4,
            "detection_accuracy": 0.3,
            "false_positive_prevention": 0.3
        }
    },
    {
        "id": "pii_003",
        "name": "Multi-PII Strict Mode",
        "description": "Test strict mode with multiple PII types",
        "category": "pii_redaction",
        "input": {
            "text": "CEO: John Smith, email: ceo@corp.com, SSN: 123-45-6789, phone: (555) 123-4567",
            "mode": "strict"
        },
        "expected": {
            "redacted_count": 4,
            "pii_types": ["email", "ssn", "phone", "name"],
            "must_redact": ["John Smith", "ceo@corp.com", "123-45-6789", "(555) 123-4567"]
        },
        "scoring_weights": {
            "detection_accuracy": 0.4,
            "redaction_completeness": 0.3,
            "strict_mode_coverage": 0.3
        }
    }
]

EXTRACTION_ACCURACY_TESTS: List[GoldenTestCase] = [
    {
        "id": "extract_001",
        "name": "P&L Metrics Extraction",
        "description": "Test extraction of standard P&L metrics",
        "category": "extraction_accuracy",
        "input": {
            "document_text": """
                Revenue: $125,000
                COGS: $31,250
                Gross Margin: 75%
                Operating Expenses: $85,000
                Net Income: $8,750
            """,
            "expected_metrics": ["revenue", "cogs", "gross_margin", "opex", "net_income"]
        },
        "expected": {
            "extracted_values": {
                "revenue": 125000,
                "cogs": 31250,
                "gross_margin": 0.75,
                "opex": 85000,
                "net_income": 8750
            },
            "accuracy_threshold": 0.95
        },
        "scoring_weights": {
            "value_accuracy": 0.5,
            "field_coverage": 0.3,
            "format_handling": 0.2
        }
    },
    {
        "id": "extract_002",
        "name": "SaaS Metrics Extraction",
        "description": "Test extraction of SaaS-specific metrics",
        "category": "extraction_accuracy",
        "input": {
            "document_text": """
                Monthly Recurring Revenue: $45K
                Annual Contract Value: $540,000
                Customer Acquisition Cost: $2,500
                Lifetime Value: $12,000
                Churn Rate: 3.5% monthly
                Net Revenue Retention: 115%
            """,
            "expected_metrics": ["mrr", "acv", "cac", "ltv", "churn", "nrr"]
        },
        "expected": {
            "extracted_values": {
                "mrr": 45000,
                "acv": 540000,
                "cac": 2500,
                "ltv": 12000,
                "churn": 0.035,
                "nrr": 1.15
            },
            "accuracy_threshold": 0.90
        },
        "scoring_weights": {
            "value_accuracy": 0.4,
            "unit_handling": 0.3,
            "field_coverage": 0.3
        }
    }
]

GOLDEN_DATASETS = {
    "cfo_analysis": CFO_ANALYSIS_TESTS,
    "market_analysis": MARKET_ANALYSIS_TESTS,
    "strategy_analysis": STRATEGY_ANALYSIS_TESTS,
    "pii_redaction": PII_REDACTION_TESTS,
    "extraction_accuracy": EXTRACTION_ACCURACY_TESTS
}

def get_dataset_by_id(dataset_id: str) -> Optional[GoldenTestCase]:
    """Retrieve a specific test case by ID."""
    for category, tests in GOLDEN_DATASETS.items():
        for test in tests:
            if test["id"] == dataset_id:
                return test
    return None

def get_datasets_by_category(category: str) -> List[GoldenTestCase]:
    """Retrieve all test cases for a category."""
    return GOLDEN_DATASETS.get(category, [])

def get_all_datasets() -> List[GoldenTestCase]:
    """Retrieve all test cases across all categories."""
    all_tests = []
    for tests in GOLDEN_DATASETS.values():
        all_tests.extend(tests)
    return all_tests
