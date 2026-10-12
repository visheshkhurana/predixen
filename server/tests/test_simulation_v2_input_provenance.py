"""Provenance for simulation_v2 inputs.

Canned baselines are assumed. Founder request fields and stored company data
are entered. Connector sync records are synced. Unknown origin is assumed.
Resolved numbers stay on the historical defaults unless a real source supplied
a value.
"""

from datetime import datetime, timezone

from pydantic import ValidationError

from server.api.simulation_v2 import SimulationV2Request, build_simulation_v2_state
from server.services.simulation.input_normalization import (
    CANNED_BASELINE,
    IMPLIED_ASSUMPTIONS,
    PROVENANCE_OMIT_UNTIL_PANEL_PR,
    inputs_for_simulation_request,
    normalize_simulation_inputs,
)


PUBLISHED_FIELDS = (
    "monthly_revenue",
    "monthly_burn",
    "cash_balance",
    "growth_rate",
    "customers",
    "churn_rate",
    "team_size",
)


def test_omit_set_is_empty_and_seven_fields_are_classified():
    """The panel is live, so revenue, burn, cash, growth, customers, churn and headcount are labelled."""
    assert PROVENANCE_OMIT_UNTIL_PANEL_PR == frozenset()

    _, assumed = normalize_simulation_inputs()
    for name in PUBLISHED_FIELDS:
        assert assumed[name] == {"kind": "assumed"}

    _, entered = normalize_simulation_inputs(
        request_fields={name: 1 for name in PUBLISHED_FIELDS}
    )
    for name in PUBLISHED_FIELDS:
        assert entered[name] == {"kind": "entered"}

    _, stored = normalize_simulation_inputs(
        company_entered={name: 2 for name in PUBLISHED_FIELDS}
    )
    for name in PUBLISHED_FIELDS:
        assert stored[name] == {"kind": "entered"}

    _, synced = normalize_simulation_inputs(
        sync_records={
            name: {"value": 3, "source": "stripe", "synced_at": "2026-01-01T00:00:00Z"}
            for name in PUBLISHED_FIELDS
        }
    )
    for name in PUBLISHED_FIELDS:
        assert synced[name]["kind"] == "synced"
        assert synced[name]["source"] == "stripe"

    _, unknown = normalize_simulation_inputs(
        origins={name: "unknown" for name in PUBLISHED_FIELDS}
    )
    for name in PUBLISHED_FIELDS:
        assert unknown[name] == {"kind": "assumed"}

    _, explicit_null = normalize_simulation_inputs(
        request_fields={name: None for name in PUBLISHED_FIELDS}
    )
    for name in PUBLISHED_FIELDS:
        assert explicit_null[name] == {"kind": "assumed"}

    request = SimulationV2Request(
        monthly_revenue=111,
        monthly_burn=222,
        cash_balance=333,
        growth_rate=0.2,
        customers=7,
        churn_rate=0.01,
        team_size=8,
        funding_climate=0.2,
    )
    values, provenance = inputs_for_simulation_request(request)
    for name in PUBLISHED_FIELDS:
        assert provenance[name] == {"kind": "entered"}
        assert values[name] == getattr(request, name)
    assert provenance["funding_climate"] == {"kind": "entered"}
    assert provenance["total_rounds"] == {"kind": "assumed"}
    assert provenance["team_morale"] == {"kind": "assumed"}


def test_canned_baseline_matches_request_model_defaults():
    for name, expected in CANNED_BASELINE.items():
        assert SimulationV2Request.model_fields[name].default == expected


def test_every_canned_baseline_is_assumed():
    values, provenance = normalize_simulation_inputs()

    for name, expected in CANNED_BASELINE.items():
        assert values[name] == expected
        assert provenance[name] == {"kind": "assumed"}

    for name, expected in IMPLIED_ASSUMPTIONS.items():
        assert values[name] == expected
        assert provenance[name] == {"kind": "assumed"}


def test_empty_request_uses_canned_baselines_as_assumed():
    request = SimulationV2Request()
    values, provenance = inputs_for_simulation_request(request)

    assert request.model_fields_set == set()
    for name, expected in CANNED_BASELINE.items():
        assert values[name] == expected
        assert getattr(request, name) == expected
        assert provenance[name] == {"kind": "assumed"}


def test_founder_request_fields_are_entered_and_other_fields_stay_assumed():
    request = SimulationV2Request(
        monthly_revenue=12345,
        cash_balance=999,
        team_size=4,
        funding_climate=0.2,
    )
    values, provenance = inputs_for_simulation_request(request)

    assert values["monthly_revenue"] == 12345
    assert values["cash_balance"] == 999
    assert values["team_size"] == 4
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert provenance["cash_balance"] == {"kind": "entered"}
    assert provenance["team_size"] == {"kind": "entered"}
    assert provenance["funding_climate"] == {"kind": "entered"}

    for name, expected in CANNED_BASELINE.items():
        if name in ("monthly_revenue", "cash_balance", "team_size", "funding_climate"):
            continue
        assert values[name] == expected
        assert provenance[name] == {"kind": "assumed"}


def test_explicit_default_value_is_still_entered():
    """A founder who submits the same number as the fallback did enter it."""
    request = SimulationV2Request(monthly_revenue=50000, monthly_burn=80000, cash_balance=500000)
    values, provenance = inputs_for_simulation_request(request)

    assert values["monthly_revenue"] == 50000
    assert values["monthly_burn"] == 80000
    assert values["cash_balance"] == 500000
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert provenance["monthly_burn"] == {"kind": "entered"}
    assert provenance["cash_balance"] == {"kind": "entered"}
    assert provenance["customers"] == {"kind": "assumed"}
    assert provenance["total_rounds"] == {"kind": "assumed"}


def test_stored_company_data_is_entered():
    values, provenance = normalize_simulation_inputs(
        company_entered={
            "team_size": 8,
            "cash_balance": {"value": 250000},
            "monthly_revenue": 0,
        }
    )

    assert values["team_size"] == 8
    assert values["cash_balance"] == 250000
    assert values["monthly_revenue"] == 0
    assert values["monthly_burn"] == 80000
    assert provenance["team_size"] == {"kind": "entered"}
    assert provenance["cash_balance"] == {"kind": "entered"}
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert provenance["monthly_burn"] == {"kind": "assumed"}
    assert provenance["total_rounds"] == {"kind": "assumed"}


def test_unknown_origin_is_assumed():
    values, provenance = normalize_simulation_inputs(
        origins={
            "monthly_revenue": "unknown",
            "not_a_field": None,
            "mystery": {"value": 99, "kind": "entered"},
            "cash_balance": "bogus",
        }
    )

    assert provenance["monthly_revenue"] == {"kind": "assumed"}
    assert values["monthly_revenue"] == 50000
    assert provenance["cash_balance"] == {"kind": "assumed"}
    assert values["cash_balance"] == 500000
    assert provenance["not_a_field"] == {"kind": "assumed"}
    assert "not_a_field" not in values
    assert provenance["mystery"] == {"kind": "assumed"}
    assert values["mystery"] == 99
    assert "source" not in provenance["mystery"]
    assert "synced_at" not in provenance["mystery"]


def test_unknown_origin_does_not_downgrade_a_founder_value():
    values, provenance = normalize_simulation_inputs(
        request_fields={"funding_climate": 0.2, "monthly_revenue": 77},
        origins={"funding_climate": "unknown", "monthly_revenue": "unknown"},
    )
    assert values["funding_climate"] == 0.2
    assert provenance["funding_climate"] == {"kind": "entered"}
    assert values["monthly_revenue"] == 77
    assert provenance["monthly_revenue"] == {"kind": "entered"}


def test_missing_field_set_treats_carried_non_null_values_as_entered():
    """No model_fields_set: non-None values are entered, nulls stay canned."""

    class Bare:
        monthly_revenue = 12345
        monthly_burn = 0
        cash_balance = None
        funding_climate = 0.2
        market_growth = None

    values, provenance = inputs_for_simulation_request(Bare())
    assert values["monthly_revenue"] == 12345
    assert values["monthly_burn"] == 0
    assert values["cash_balance"] == 500000
    assert values["growth_rate"] == 0.05
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert provenance["monthly_burn"] == {"kind": "entered"}
    assert provenance["cash_balance"] == {"kind": "assumed"}
    assert provenance["growth_rate"] == {"kind": "assumed"}
    assert values["funding_climate"] == 0.2
    assert provenance["funding_climate"] == {"kind": "entered"}
    assert values["market_growth"] == 0.5
    assert provenance["market_growth"] == {"kind": "assumed"}
    assert provenance["team_morale"] == {"kind": "assumed"}


def test_omitted_mrr_burn_cash_growth_are_assumed_canned_values():
    request = SimulationV2Request(
        total_rounds=12,
        customers=20,
        team_size=4,
        churn_rate=0.01,
        funding_climate=0.2,
        market_growth=0.4,
        market_volatility=0.2,
    )
    assert "monthly_revenue" not in request.model_fields_set
    assert "monthly_burn" not in request.model_fields_set
    assert "cash_balance" not in request.model_fields_set
    assert "growth_rate" not in request.model_fields_set

    values, provenance = inputs_for_simulation_request(request)
    assert values["monthly_revenue"] == 50000
    assert values["monthly_burn"] == 80000
    assert values["cash_balance"] == 500000
    assert values["growth_rate"] == 0.05
    assert values["customers"] == 20
    for name in ("monthly_revenue", "monthly_burn", "cash_balance", "growth_rate"):
        assert provenance[name] == {"kind": "assumed"}
    assert provenance["customers"] == {"kind": "entered"}
    assert provenance["team_size"] == {"kind": "entered"}
    assert provenance["churn_rate"] == {"kind": "entered"}
    assert provenance["funding_climate"] == {"kind": "entered"}
    assert provenance["total_rounds"] == {"kind": "entered"}


def test_explicit_null_is_assumed_not_entered():
    """Explicit null is assumed. The schema rejects JSON null on float fields,
    so this uses a request that carries None the way a nullable payload would.
    """
    payload = {
        "monthly_revenue": None,
        "monthly_burn": None,
        "cash_balance": None,
        "growth_rate": None,
    }
    try:
        request = SimulationV2Request.model_validate(payload)
    except ValidationError:
        request = SimulationV2Request.model_construct(**payload)

    assert request.monthly_revenue is None
    assert "monthly_revenue" in request.model_fields_set
    values, provenance = inputs_for_simulation_request(request)
    assert values["monthly_revenue"] == 50000
    assert values["monthly_burn"] == 80000
    assert values["cash_balance"] == 500000
    assert values["growth_rate"] == 0.05
    for name in ("monthly_revenue", "monthly_burn", "cash_balance", "growth_rate"):
        assert provenance[name] == {"kind": "assumed"}
        assert provenance[name]["kind"] != "entered"


def test_synced_record_passes_through_source_and_synced_at():
    synced_at = datetime(2026, 4, 1, 12, 30, tzinfo=timezone.utc)
    values, provenance = normalize_simulation_inputs(
        sync_records={
            "funding_climate": {
                "value": 0.2,
                "source": "stripe",
                "synced_at": "2026-01-02T03:04:05Z",
            },
            "market_growth": {
                "value": 0.4,
                "source": "mercury",
                "synced_at": synced_at,
            },
            "market_volatility": {
                "market_volatility": 0.2,
                "source": "quickbooks",
                "synced_at": "2026-05-01T00:00:00Z",
            },
            "total_rounds": {"value": 12},
            "monthly_revenue": {
                "value": 42000,
                "source": "stripe",
                "synced_at": "2026-01-02T03:04:05Z",
            },
            "customers": {"value": 12},
            "team_size": 9,
        }
    )

    assert provenance["funding_climate"] == {
        "kind": "synced",
        "source": "stripe",
        "synced_at": "2026-01-02T03:04:05Z",
    }
    assert values["market_growth"] == 0.4
    assert provenance["market_growth"] == {
        "kind": "synced",
        "source": "mercury",
        "synced_at": "2026-04-01T12:30:00+00:00",
    }
    assert values["market_volatility"] == 0.2
    assert provenance["market_volatility"]["kind"] == "synced"
    assert provenance["market_volatility"]["source"] == "quickbooks"
    assert provenance["total_rounds"] == {"kind": "synced"}
    assert values["total_rounds"] == 12
    assert values["monthly_revenue"] == 42000
    assert values["customers"] == 12
    assert values["team_size"] == 9
    assert provenance["monthly_revenue"] == {
        "kind": "synced",
        "source": "stripe",
        "synced_at": "2026-01-02T03:04:05Z",
    }
    assert provenance["customers"] == {"kind": "synced"}
    assert provenance["team_size"] == {"kind": "synced"}


def test_synced_zero_is_kept():
    values, provenance = normalize_simulation_inputs(
        sync_records={"funding_climate": {"value": 0, "source": "stripe"}}
    )
    assert values["funding_climate"] == 0
    assert provenance["funding_climate"] == {"kind": "synced", "source": "stripe"}


def test_sync_without_metadata_omits_source_and_synced_at():
    _, provenance = normalize_simulation_inputs(
        sync_records={
            "funding_climate": {"value": 0.3, "source": "", "synced_at": None},
            "market_growth": {"value": 0.4, "source": 12, "synced_at": 1700000000},
        }
    )
    assert provenance["funding_climate"] == {"kind": "synced"}
    assert provenance["market_growth"] == {"kind": "synced"}


def test_sync_record_without_a_number_does_not_claim_the_canned_baseline():
    values, provenance = normalize_simulation_inputs(
        sync_records={
            "monthly_revenue": {"source": "stripe", "synced_at": "2026-01-01T00:00:00Z"},
            "funding_climate": {"source": "stripe", "synced_at": "2026-01-01T00:00:00Z"},
        }
    )
    assert values["monthly_revenue"] == 50000
    assert provenance["monthly_revenue"] == {"kind": "assumed"}
    assert values["funding_climate"] == 0.6
    assert provenance["funding_climate"] == {"kind": "assumed"}


def test_founder_request_beats_sync_and_company_and_sync_beats_company():
    values, provenance = normalize_simulation_inputs(
        request_fields={"funding_climate": 0.2, "monthly_revenue": 1},
        company_entered={"funding_climate": 0.3, "market_growth": 0.4, "customers": 4},
        sync_records={
            "funding_climate": {
                "value": 0.9,
                "source": "stripe",
                "synced_at": "2026-01-01T00:00:00Z",
            },
            "market_growth": {"value": 0.8, "source": "stripe"},
            "market_volatility": {
                "value": 0.25,
                "source": "brex",
                "synced_at": "2026-02-02T00:00:00Z",
            },
            "monthly_burn": {"value": 6, "source": "stripe"},
        },
    )

    assert values["funding_climate"] == 0.2
    assert provenance["funding_climate"] == {"kind": "entered"}
    assert values["market_growth"] == 0.8
    assert provenance["market_growth"]["kind"] == "synced"
    assert "source" not in provenance["funding_climate"]
    assert values["market_volatility"] == 0.25
    assert provenance["market_volatility"]["kind"] == "synced"
    assert provenance["market_volatility"]["source"] == "brex"
    assert values["monthly_revenue"] == 1
    assert values["customers"] == 4
    assert values["monthly_burn"] == 6
    assert values["team_size"] == 10
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert provenance["customers"] == {"kind": "entered"}
    assert provenance["monthly_burn"] == {"kind": "synced", "source": "stripe"}
    assert provenance["cash_balance"] == {"kind": "assumed"}
    assert provenance["growth_rate"] == {"kind": "assumed"}
    assert provenance["churn_rate"] == {"kind": "assumed"}
    assert provenance["team_size"] == {"kind": "assumed"}


def test_claimed_entered_or_synced_without_a_value_stays_assumed():
    values, provenance = normalize_simulation_inputs(
        origins={"funding_climate": "entered", "market_growth": "synced", "monthly_revenue": "entered"}
    )
    assert values["funding_climate"] == 0.6
    assert provenance["funding_climate"] == {"kind": "assumed"}
    assert values["market_growth"] == 0.5
    assert provenance["market_growth"] == {"kind": "assumed"}
    assert values["monthly_revenue"] == 50000
    assert provenance["monthly_revenue"] == {"kind": "assumed"}


def test_normalised_inputs_match_historical_state_math():
    """Engine inputs stay on the request numbers, including the 999 runway fallback."""
    request = SimulationV2Request(
        monthly_revenue=20000,
        monthly_burn=0,
        cash_balance=400000,
        customers=15,
        team_size=6,
        growth_rate=0.2,
        churn_rate=0.01,
        funding_climate=0.2,
        market_growth=0.4,
        market_volatility=0.2,
        total_rounds=12,
    )
    normalized, provenance = inputs_for_simulation_request(request)
    state, scenario_params, total_rounds = build_simulation_v2_state(normalized)

    assert state.mrr == request.monthly_revenue
    assert state.arr == request.monthly_revenue * 12
    assert state.burn_rate == request.monthly_burn
    assert state.cash == request.cash_balance
    assert state.runway_months == 999
    assert state.customers == request.customers
    assert state.churn_rate == request.churn_rate
    assert state.team_size == request.team_size
    assert state.growth_rate == request.growth_rate
    assert state.team_morale == 0.7
    assert state.product_quality == 0.5
    assert state.market_fit == 0.5
    assert state.brand_reputation == 0.5
    assert state.investor_confidence == 0.5
    assert scenario_params == {
        "funding_climate": request.funding_climate,
        "market_growth": request.market_growth,
        "market_volatility": request.market_volatility,
    }
    assert total_rounds == request.total_rounds
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert provenance["monthly_burn"] == {"kind": "entered"}
    assert provenance["cash_balance"] == {"kind": "entered"}
    assert provenance["customers"] == {"kind": "entered"}
    assert provenance["team_size"] == {"kind": "entered"}
    assert provenance["growth_rate"] == {"kind": "entered"}
    assert provenance["churn_rate"] == {"kind": "entered"}
    assert provenance["funding_climate"] == {"kind": "entered"}
    assert provenance["team_morale"] == {"kind": "assumed"}


def test_default_request_state_matches_historical_fallbacks():
    request = SimulationV2Request()
    normalized, provenance = inputs_for_simulation_request(request)
    state, scenario_params, total_rounds = build_simulation_v2_state(normalized)

    assert state.mrr == 50000
    assert state.arr == 50000 * 12
    assert state.burn_rate == 80000
    assert state.cash == 500000
    assert state.runway_months == 500000 / 80000
    assert state.customers == 50
    assert state.churn_rate == 0.03
    assert state.team_size == 10
    assert state.growth_rate == 0.05
    assert state.team_morale == 0.7
    assert state.product_quality == 0.5
    assert state.market_fit == 0.5
    assert state.brand_reputation == 0.5
    assert state.investor_confidence == 0.5
    assert scenario_params == {
        "funding_climate": 0.6,
        "market_growth": 0.5,
        "market_volatility": 0.1,
    }
    assert total_rounds == 24
    assert PROVENANCE_OMIT_UNTIL_PANEL_PR == frozenset()
    visible = set(CANNED_BASELINE) | set(IMPLIED_ASSUMPTIONS)
    assert set(provenance) >= visible
    for name in PUBLISHED_FIELDS:
        assert provenance[name] == {"kind": "assumed"}
    assert all(item["kind"] == "assumed" for item in provenance.values())


def test_provenance_does_not_replace_existing_response_keys():
    existing = {
        "simulation_id": "sim_x",
        "status": "completed",
        "total_rounds": 24,
        "total_actions": 3,
        "initial_state": {"mrr": 50000},
        "final_state": {"mrr": 51000},
        "report": {"outcome_score": 70},
        "rounds": [],
        "all_actions": [],
        "agents": [],
    }
    _, provenance = inputs_for_simulation_request(SimulationV2Request(monthly_revenue=111))
    complete = {**existing, "input_provenance": provenance}

    for key, value in existing.items():
        assert complete[key] == value
    assert complete["input_provenance"]["monthly_revenue"] == {"kind": "entered"}
    assert complete["input_provenance"]["monthly_burn"] == {"kind": "assumed"}
    assert complete["input_provenance"]["total_rounds"] == {"kind": "assumed"}


def test_null_base_metrics_are_not_entered():
    """mrr, burn, cash and growth omitted by the client come back assumed, not entered.

    This is the request /simulate builds when those baseMetrics are null.
    customers and churn are not posted either; the engine's canned defaults apply.
    """
    payload = {
        "total_rounds": 12,
        "funding_climate": 0.6,
        "market_growth": 0.5,
        "market_volatility": 0.1,
    }
    for key in (
        "monthly_revenue",
        "monthly_burn",
        "cash_balance",
        "growth_rate",
        "customers",
        "churn_rate",
        "team_size",
    ):
        assert key not in payload

    request = SimulationV2Request.model_validate(payload)
    values, provenance = inputs_for_simulation_request(request)
    assert values["monthly_revenue"] == 50000
    assert values["monthly_burn"] == 80000
    assert values["cash_balance"] == 500000
    assert values["growth_rate"] == 0.05
    assert values["customers"] == 50
    assert values["churn_rate"] == 0.03
    assert values["team_size"] == 10
    for name in ("monthly_revenue", "monthly_burn", "cash_balance", "growth_rate", "customers", "churn_rate", "team_size"):
        assert provenance[name] == {"kind": "assumed"}
        assert provenance[name]["kind"] != "entered"
