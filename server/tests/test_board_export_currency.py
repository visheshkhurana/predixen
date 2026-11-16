"""Board deck text states money in the company's currency, and a profitable
company is never described as burning a negative amount with 0 months runway."""
from server.api import board_export as be


def _data(currency, burn, runway=0.0, sustainable=False):
    return {
        "company": {"name": "Chai Point Direct", "currency": currency},
        "metrics": {
            "monthly_revenue": 2_500_000, "mrr": 2_500_000, "arr": 30_000_000,
            "burn_rate": burn, "cash_balance": 30_000_000, "runway_months": runway,
            "runway_sustainable": sustainable, "is_profitable": burn < 0,
            "gross_margin": 55.0, "revenue_growth": 0.0, "headcount": 14, "churn_rate": 0.0,
            "cac": None, "ltv": None, "ltv_cac_ratio": None, "ndr": None, "customers": None,
        },
        "confidence": 56, "scenarios": [], "decisions": [], "simulation": {},
        "fundraising_rounds": [{"name": "Seed", "target_raise": 50_000_000, "pre_money_valuation": 200_000_000}],
    }


def test_money_formats():
    assert be._money(2_500_000, "INR") == "₹25,00,000"
    assert be._money(30_000_000, "INR") == "₹3,00,00,000"
    assert be._money(950, "INR") == "₹950"
    assert be._money(2_500_000, "USD") == "$2,500,000"
    assert be._money(149, "AED") == "AED 149"


def test_inr_profitable_fallback_has_no_dollars_or_negative_burn():
    data = _data("INR", burn=-575_000, sustainable=True)
    for title in ("Executive Summary", "Traction", "Risks", "Use of Funds and Milestones", "Recommendations", "Other"):
        text = be._generate_fallback_narrative({"title": title}, data)
        assert "$" not in text, (title, text)
        assert "-₹" not in text and "₹-" not in text, (title, text)
        assert "0.0 months" not in text, (title, text)
    exec_text = be._generate_fallback_narrative({"title": "Executive Summary"}, data)
    assert "₹25,00,000" in exec_text
    assert "not burning cash (monthly surplus of ₹5,75,000)" in exec_text


def test_prompt_uses_company_currency_and_real_burn():
    prompt = be._build_narrative_prompt("investor_update", {"title": "Executive Summary"}, _data("INR", burn=-575_000, sustainable=True))
    assert "MRR: ₹25,00,000" in prompt
    assert "Net Burn: not burning cash" in prompt
    assert "Currency: INR" in prompt
    assert "Target ₹5,00,00,000" in prompt
    assert "$" not in prompt.split("Data Confidence")[0]


def test_usd_burning_company_reads_as_before():
    data = _data("USD", burn=40_000, runway=18.5)
    text = be._generate_fallback_narrative({"title": "Executive Summary"}, data)
    assert "$2,500,000" in text and "$40,000/month net burn" in text and "18.5 months" in text


def test_unknown_burn_is_not_break_even():
    data = _data("INR", burn=-1)
    data["metrics"]["burn_rate"] = None
    data["metrics"]["runway_months"] = 0
    prompt = be._build_narrative_prompt("investor_update", {"title": "Executive Summary"}, data)
    assert "Net Burn: net burn not available" in prompt
    assert "break-even" not in prompt
    for title in ("Executive Summary", "Risks", "Use of Funds and Milestones", "Other"):
        text = be._generate_fallback_narrative({"title": title}, data)
        assert "break-even" not in text and "covers costs" not in text, (title, text)
        assert "0.0 months" not in text, (title, text)
