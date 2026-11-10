import numpy as np
import pandas as pd
import pytest

from pmo_tracker import charts, config, metrics
from pmo_tracker.data import generate


@pytest.fixture(scope="module")
def d():
    data = generate(n_projects=12, seed=5)
    data["projects"] = metrics.add_performance(data["projects"])
    data["risks"] = metrics.add_risk_scores(data["risks"])
    return data


@pytest.mark.parametrize("idx,expected", [(1.0, "Green"), (0.95, "Green"), (0.9, "Amber"), (0.85, "Amber"), (0.7, "Red")])
def test_rag(idx, expected):
    assert metrics.rag(idx) == expected


@pytest.mark.parametrize("score,band", [(1, "Low"), (4, "Low"), (6, "Medium"), (12, "High"), (25, "Critical")])
def test_risk_band(score, band):
    assert metrics.risk_band(score) == band


def test_every_project_linked_to_objective(d):
    assert d["projects"]["objective_id"].isin(config.STRATEGIC_OBJECTIVES).all()


def test_overall_rag_is_worst_of_components(d):
    order = {"Green": 0, "Amber": 1, "Red": 2}
    p = d["projects"]
    worst = [max(order[a], order[b]) for a, b in zip(p["schedule_rag"], p["cost_rag"])]
    assert [order[x] for x in p["overall_rag"]] == worst


def test_risk_matrix_counts_open_risks(d):
    m = metrics.risk_matrix(d["risks"])
    assert m.shape == (5, 5)
    assert m.values.sum() == (d["risks"]["status"] != "Closed").sum()


def test_summary(d):
    s = metrics.portfolio_summary(d["projects"], d["risks"], d["milestones"])
    assert s["projects"] == 12
    assert sum(s["rag_counts"].values()) == 12
    assert 0 <= s["milestones_complete_pct"] <= 100


def test_budget_cumulative(d):
    b = metrics.budget_by_month(d["financials"])
    assert b["cum_actual"].is_monotonic_increasing
    assert b["cum_actual"].iloc[-1] == pytest.approx(d["financials"]["actual_sar"].sum())


def test_spend_matches_actual_cost(d):
    spend = d["financials"].groupby("project_id")["actual_sar"].sum()
    ac = d["projects"].set_index("project_id")["actual_cost"].loc[spend.index]
    pd.testing.assert_series_equal(spend, ac, check_names=False, rtol=1e-6)


def test_charts_build(d):
    p, r, m = d["projects"], d["risks"], d["milestones"]
    assert charts.rag_donut(metrics.portfolio_summary(p, r, m)["rag_counts"]).data
    assert charts.strategy_sunburst(p).data
    assert charts.milestone_gantt(p, m, pd.Timestamp("2025-09-30")).data
    assert charts.risk_heatmap(metrics.risk_matrix(r)).data
    assert charts.budget_chart(metrics.budget_by_month(d["financials"])).data


def test_eac_scenario_improves_with_gain(d):
    p = metrics.add_performance(d["projects"])
    base = metrics.eac_scenario(p, 0, 0)
    better = metrics.eac_scenario(p, 0.1, 0.1)
    assert better["scenario_eac_sar"].sum() <= base["scenario_eac_sar"].sum()
    assert (better["scenario_slip_days"] <= base["scenario_slip_days"]).all()
    assert np.allclose(base["scenario_eac_sar"], base["baseline_eac_sar"])


def test_priority_scores_bounded_and_ranked(d):
    p = metrics.add_performance(d["projects"])
    r = metrics.add_risk_scores(d["risks"])
    s = metrics.priority_scores(p, r, {"strategic": 4, "delivery": 3, "risk": 2, "cost": 1})
    assert s["priority_score"].between(0, 100).all()
    assert s["priority_score"].is_monotonic_decreasing
    assert sorted(s["rank"]) == list(range(1, len(s) + 1))


def test_priority_only_strategic_weight_follows_benefit(d):
    p = metrics.add_performance(d["projects"])
    r = metrics.add_risk_scores(d["risks"])
    s = metrics.priority_scores(p, r, {"strategic": 1})
    assert s["benefit_score"].is_monotonic_decreasing


def test_spend_by_programme_is_cumulative(d):
    p = metrics.add_performance(d["projects"])
    t = metrics.spend_by_programme_month(d["financials"], p)
    for _, g in t.groupby("programme"):
        assert g["cum_actual_sar"].is_monotonic_increasing
    assert t["cum_actual_sar"].groupby(t["month"]).sum().max() == pytest.approx(d["financials"]["actual_sar"].sum())


def test_new_pmo_charts_build(d):
    p = metrics.add_performance(d["projects"])
    r = metrics.add_risk_scores(d["risks"])
    charts.spend_race(metrics.spend_by_programme_month(d["financials"], p))
    charts.s_curve(metrics.project_s_curve(d["financials"], p["project_id"].iloc[0]), "x")
    charts.scenario_eac_bar(metrics.eac_scenario(p, 0.05, 0.05))
    charts.priority_bar(metrics.priority_scores(p, r, {"strategic": 1, "delivery": 1, "risk": 1, "cost": 1}))


def test_priority_contributions_sum_to_score(d):
    s = metrics.priority_scores(d["projects"], d["risks"], {"strategic": 4, "delivery": 3, "risk": 2, "cost": 1})
    parts = s[["strategic_contrib", "delivery_contrib", "risk_contrib", "cost_contrib"]].sum(axis=1)
    assert np.allclose(parts.round(1), s["priority_score"], atol=0.11)
