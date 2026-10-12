"""Provenance for simulation_v2 inputs.

Canned baselines are assumed. Founder request fields and stored company data
are entered. Connector sync records are synced. Unknown origin is assumed.
Resolved numbers stay on the historical defaults unless a real source supplied
a value.
"""

from datetime import datetime, timezone

from server.api.simulation_v2 import SimulationV2Request, build_simulation_v2_state
from server.services.simulation.input_normalization import (
    CANNED_BASELINE,
    IMPLIED_ASSUMPTIONS,
    inputs_for_simulation_request,
    normalize_simulation_inputs,
)


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
    )
    values, provenance = inputs_for_simulation_request(request)

    assert values["monthly_revenue"] == 12345
    assert values["cash_balance"] == 999
    assert values["team_size"] == 4
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert provenance["cash_balance"] == {"kind": "entered"}
    assert provenance["team_size"] == {"kind": "entered"}

    for name, expected in CANNED_BASELINE.items():
        if name in ("monthly_revenue", "cash_balance", "team_size"):
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


def test_stored_company_data_is_entered():
    values, provenance = normalize_simulation_inputs(
        company_entered={
            "team_size": 8,
            "cash_balance": {"value": 250000},
            "monthly_revenue": 0,
        }
    )

    assert values["team_size"] == 8
    assert provenance["team_size"] == {"kind": "entered"}
    assert values["cash_balance"] == 250000
    assert provenance["cash_balance"] == {"kind": "entered"}
    assert values["monthly_revenue"] == 0
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert provenance["monthly_burn"] == {"kind": "assumed"}
    assert values["monthly_burn"] == 80000


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
        request_fields={"monthly_revenue": 77},
        origins={"monthly_revenue": "unknown"},
    )
    assert values["monthly_revenue"] == 77
    assert provenance["monthly_revenue"] == {"kind": "entered"}


def test_request_without_field_metadata_is_assumed():
    class Bare:
        monthly_revenue = 50000

    _, provenance = inputs_for_simulation_request(Bare())
    assert provenance["monthly_revenue"] == {"kind": "assumed"}
    assert provenance["team_morale"] == {"kind": "assumed"}


def test_synced_record_passes_through_source_and_synced_at():
    synced_at = datetime(2026, 4, 1, 12, 30, tzinfo=timezone.utc)
    values, provenance = normalize_simulation_inputs(
        sync_records={
            "monthly_revenue": {
                "value": 42000,
                "source": "stripe",
                "synced_at": "2026-01-02T03:04:05Z",
            },
            "cash_balance": {
                "value": 1000,
                "source": "mercury",
                "synced_at": synced_at,
            },
            "monthly_burn": {
                "monthly_burn": 33333,
                "source": "quickbooks",
                "synced_at": "2026-05-01T00:00:00Z",
            },
            "customers": {"value": 12},
            "team_size": 9,
        }
    )

    assert values["monthly_revenue"] == 42000
    assert provenance["monthly_revenue"] == {
        "kind": "synced",
        "source": "stripe",
        "synced_at": "2026-01-02T03:04:05Z",
    }
    assert values["cash_balance"] == 1000
    assert provenance["cash_balance"] == {
        "kind": "synced",
        "source": "mercury",
        "synced_at": "2026-04-01T12:30:00+00:00",
    }
    assert values["monthly_burn"] == 33333
    assert provenance["monthly_burn"]["kind"] == "synced"
    assert provenance["monthly_burn"]["source"] == "quickbooks"
    assert provenance["customers"] == {"kind": "synced"}
    assert values["customers"] == 12
    assert provenance["team_size"] == {"kind": "synced"}
    assert values["team_size"] == 9


def test_synced_zero_is_kept():
    values, provenance = normalize_simulation_inputs(
        sync_records={"monthly_revenue": {"value": 0, "source": "stripe"}}
    )
    assert values["monthly_revenue"] == 0
    assert provenance["monthly_revenue"] == {"kind": "synced", "source": "stripe"}


def test_sync_without_metadata_omits_source_and_synced_at():
    _, provenance = normalize_simulation_inputs(
        sync_records={
            "customers": {"value": 9, "source": "", "synced_at": None},
            "churn_rate": {"value": 0.02, "source": 12, "synced_at": 1700000000},
        }
    )
    assert provenance["customers"] == {"kind": "synced"}
    assert provenance["churn_rate"] == {"kind": "synced"}


def test_sync_record_without_a_number_does_not_claim_the_canned_baseline():
    values, provenance = normalize_simulation_inputs(
        sync_records={
            "monthly_revenue": {"source": "stripe", "synced_at": "2026-01-01T00:00:00Z"},
        }
    )
    assert values["monthly_revenue"] == 50000
    assert provenance["monthly_revenue"] == {"kind": "assumed"}


def test_founder_request_beats_sync_and_company_and_sync_beats_company():
    values, provenance = normalize_simulation_inputs(
        request_fields={"monthly_revenue": 1},
        company_entered={"monthly_revenue": 2, "monthly_burn": 3, "customers": 4},
        sync_records={
            "monthly_revenue": {
                "value": 5,
                "source": "stripe",
                "synced_at": "2026-01-01T00:00:00Z",
            },
            "monthly_burn": {"value": 6, "source": "stripe"},
            "cash_balance": {
                "value": 7,
                "source": "brex",
                "synced_at": "2026-02-02T00:00:00Z",
            },
        },
    )

    assert values["monthly_revenue"] == 1
    assert provenance["monthly_revenue"] == {"kind": "entered"}
    assert values["monthly_burn"] == 6
    assert provenance["monthly_burn"]["kind"] == "synced"
    assert "source" not in provenance["monthly_revenue"]
    assert values["cash_balance"] == 7
    assert provenance["cash_balance"]["kind"] == "synced"
    assert provenance["cash_balance"]["source"] == "brex"
    assert values["customers"] == 4
    assert provenance["customers"] == {"kind": "entered"}
    assert values["team_size"] == 10
    assert provenance["team_size"] == {"kind": "assumed"}


def test_claimed_entered_or_synced_without_a_value_stays_assumed():
    values, provenance = normalize_simulation_inputs(
        origins={"monthly_revenue": "entered", "monthly_burn": "synced"}
    )
    assert values["monthly_revenue"] == 50000
    assert provenance["monthly_revenue"] == {"kind": "assumed"}
    assert values["monthly_burn"] == 80000
    assert provenance["monthly_burn"] == {"kind": "assumed"}


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
    assert provenance["monthly_burn"] == {"kind": "entered"}
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
    assert set(provenance) >= set(CANNED_BASELINE) | set(IMPLIED_ASSUMPTIONS)
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
