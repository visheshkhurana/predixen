from fastapi import APIRouter

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

@router.get("/steps")
def get_onboarding_steps():
    return {
        "steps": [
            {"id": 1, "name": "Create Account", "description": "Sign up with email or Google", "required": True},
            {"id": 2, "name": "Company Profile", "description": "Tell us about your company", "required": True},
            {"id": 3, "name": "Upload Data", "description": "Upload financials or connect integrations", "required": False},
            {"id": 4, "name": "Run First Simulation", "description": "Try a scenario with sample or real data", "required": False},
        ],
        "total_steps": 4
    }

@router.get("/industries")
def get_industries():
    return {
        "industries": [
            {"id": "saas", "name": "SaaS / Software", "benchmarks_available": True},
            {"id": "ecommerce", "name": "E-Commerce", "benchmarks_available": True},
            {"id": "fintech", "name": "Fintech", "benchmarks_available": True},
            {"id": "healthtech", "name": "HealthTech", "benchmarks_available": True},
            {"id": "marketplace", "name": "Marketplace", "benchmarks_available": True},
            {"id": "edtech", "name": "EdTech", "benchmarks_available": False},
            {"id": "other", "name": "Other", "benchmarks_available": False}
        ]
    }
