"""Portfolio metrics: earned value indices, RAG status, risk scoring and roll-ups."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def rag(index: float) -> str:
    if index >= config.RAG_RULES["green"]:
        return "Green"
    if index >= config.RAG_RULES["amber"]:
        return "Amber"
    return "Red"


def add_performance(projects: pd.DataFrame) -> pd.DataFrame:
    """Add SPI, CPI, schedule/cost/overall RAG and estimate at completion (EAC)."""
    df = projects.copy()
    df["spi"] = np.where(df["planned_value"] > 0, df["earned_value"] / df["planned_value"].replace(0, np.nan), 1.0)
    df["spi"] = df["spi"].fillna(1.0)
    df["cpi"] = np.where(df["actual_cost"] > 0, df["earned_value"] / df["actual_cost"].replace(0, np.nan), 1.0)
    df["cpi"] = df["cpi"].fillna(1.0)
    df["schedule_rag"] = df["spi"].apply(rag)
    df["cost_rag"] = df["cpi"].apply(rag)
    order = {"Green": 0, "Amber": 1, "Red": 2}
    df["overall_rag"] = [max(a, b, key=order.get) for a, b in zip(df["schedule_rag"], df["cost_rag"])]
    df["eac_sar"] = df["budget_sar"] / df["cpi"]
    df["variance_at_completion_sar"] = df["budget_sar"] - df["eac_sar"]
    return df


def risk_band(score: int) -> str:
    for band, (lo, hi) in config.RISK_BANDS.items():
        if lo <= score <= hi:
            return band
    raise ValueError(score)


def add_risk_scores(risks: pd.DataFrame) -> pd.DataFrame:
    df = risks.copy()
    df["score"] = df["likelihood"] * df["impact"]
    df["band"] = df["score"].apply(risk_band)
    return df


def risk_matrix(risks: pd.DataFrame) -> pd.DataFrame:
    """5x5 count matrix (rows = impact 5..1, cols = likelihood 1..5) of open risks."""
    open_r = risks[risks["status"] != "Closed"]
    m = pd.crosstab(open_r["impact"], open_r["likelihood"]).reindex(index=range(5, 0, -1), columns=range(1, 6),
                                                                    fill_value=0)
    return m


def portfolio_summary(projects: pd.DataFrame, risks: pd.DataFrame, milestones: pd.DataFrame) -> dict:
    p = projects
    open_r = risks[risks["status"] != "Closed"]
    return {
        "projects": len(p),
        "budget_sar": float(p["budget_sar"].sum()),
        "actual_cost_sar": float(p["actual_cost"].sum()),
        "earned_value_sar": float(p["earned_value"].sum()),
        "portfolio_spi": float(p["earned_value"].sum() / max(p["planned_value"].sum(), 1)),
        "portfolio_cpi": float(p["earned_value"].sum() / max(p["actual_cost"].sum(), 1)),
        "rag_counts": p["overall_rag"].value_counts().reindex(["Green", "Amber", "Red"], fill_value=0).to_dict(),
        "open_risks": len(open_r),
        "high_critical_risks": int(open_r["band"].isin(["High", "Critical"]).sum()),
        "milestones_overdue": int((milestones["status"] == "Overdue").sum()),
        "milestones_complete_pct": float((milestones["status"] == "Complete").mean() * 100),
    }


def objective_rollup(projects: pd.DataFrame) -> pd.DataFrame:
    g = projects.groupby(["objective_id", "objective"])
    out = g.agg(projects=("project_id", "count"), budget_sar=("budget_sar", "sum"),
                avg_progress=("actual_pct", "mean"), ev=("earned_value", "sum"), pv=("planned_value", "sum"),
                red=("overall_rag", lambda s: (s == "Red").sum())).reset_index()
    out["spi"] = out["ev"] / out["pv"].replace(0, np.nan)
    out["rag"] = out["spi"].fillna(1).apply(rag)
    return out.drop(columns=["ev", "pv"])


def budget_by_month(financials: pd.DataFrame) -> pd.DataFrame:
    t = financials.groupby("month", as_index=False)[["planned_sar", "actual_sar"]].sum()
    t["cum_planned"] = t["planned_sar"].cumsum()
    t["cum_actual"] = t["actual_sar"].cumsum()
    return t


def eac_scenario(projects: pd.DataFrame, cpi_gain: float = 0.0, spi_gain: float = 0.0) -> pd.DataFrame:
    """Re-forecast cost and finish date if performance on the REMAINING work improves.

    EAC = AC + (BAC - EV) / CPI_future, where CPI_future = current CPI + cpi_gain (capped at 1.25).
    Forecast duration = planned duration / SPI_future (simple schedule-index projection).
    """
    df = projects.copy()
    bac, ev, ac = df["budget_sar"], df["earned_value"], df["actual_cost"]
    cpi_f = (df["cpi"] + cpi_gain).clip(0.3, 1.25)
    spi_f = (df["spi"] + spi_gain).clip(0.3, 1.25)
    df["scenario_eac_sar"] = ac + (bac - ev).clip(lower=0) / cpi_f
    df["baseline_eac_sar"] = ac + (bac - ev).clip(lower=0) / df["cpi"].clip(0.3, 1.25)
    duration = (pd.to_datetime(df["end"]) - pd.to_datetime(df["start"])).dt.days
    df["baseline_slip_days"] = (duration / df["spi"].clip(0.3, 1.25) - duration).round()
    df["scenario_slip_days"] = (duration / spi_f - duration).round()
    return df


def priority_scores(projects: pd.DataFrame, risks: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Weighted multi-criteria score (0-100) for portfolio prioritisation.

    Criteria (each scaled 0-1, higher = more attractive):
      strategic  benefit_score (1-5)
      delivery   min(SPI, CPI) performance
      risk       1 - normalised sum of open-risk scores
      cost       1 - normalised budget (smaller investments score higher)
    """
    df = projects.copy()
    open_r = risks[risks["status"] != "Closed"].groupby("project_id")["score"].sum()
    rs = df["project_id"].map(open_r).fillna(0)
    crit = pd.DataFrame({
        "strategic": (df["benefit_score"] - 1) / 4,
        "delivery": (df[["spi", "cpi"]].min(axis=1).clip(0.6, 1.1) - 0.6) / 0.5,
        "risk": 1 - rs / max(rs.max(), 1),
        "cost": 1 - (df["budget_sar"] - df["budget_sar"].min()) / max(df["budget_sar"].max() - df["budget_sar"].min(), 1),
    }, index=df.index)
    w = pd.Series(weights, dtype=float).reindex(crit.columns).fillna(0)
    total = w.sum() or 1.0
    df["priority_score"] = (crit.mul(w, axis=1).sum(axis=1) / total * 100).round(1)
    for c in crit.columns:
        df[f"{c}_score"] = (crit[c] * 100).round(0)
        df[f"{c}_contrib"] = crit[c] * w[c] / total * 100  # stacked parts add up to priority_score
    df["rank"] = df["priority_score"].rank(ascending=False, method="first").astype(int)
    return df.sort_values("rank")


def spend_by_programme_month(financials: pd.DataFrame, projects: pd.DataFrame) -> pd.DataFrame:
    """Cumulative actual spend per programme for every month (frames for the animated chart)."""
    f = financials.merge(projects[["project_id", "programme", "objective_id"]], on="project_id")
    t = f.groupby(["month", "programme", "objective_id"], as_index=False)["actual_sar"].sum()
    full = pd.MultiIndex.from_product([sorted(t["month"].unique()), sorted(t["programme"].unique())],
                                      names=["month", "programme"])
    t = t.set_index(["month", "programme"])["actual_sar"].reindex(full, fill_value=0).reset_index()
    t["objective_id"] = t["programme"].map(f.drop_duplicates("programme").set_index("programme")["objective_id"])
    t["cum_actual_sar"] = t.groupby("programme")["actual_sar"].cumsum()
    return t


def project_s_curve(financials: pd.DataFrame, project_id: str) -> pd.DataFrame:
    f = financials[financials["project_id"] == project_id].sort_values("month").copy()
    f["cum_planned"] = f["planned_sar"].cumsum()
    f["cum_actual"] = f["actual_sar"].cumsum()
    return f
