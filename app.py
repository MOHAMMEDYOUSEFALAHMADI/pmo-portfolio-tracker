"""PMO Portfolio & Strategy Execution Tracker - Streamlit app (synthetic data)."""
from pathlib import Path

import pandas as pd
import streamlit as st

from pmo_tracker import charts, config, metrics, ui
from pmo_tracker.data import generate

DATA = Path(__file__).parent / "data"
AS_OF = pd.Timestamp("2025-09-30")
st.set_page_config(page_title="PMO Portfolio Tracker", page_icon="📊", layout="wide")
ui.inject_css()


@st.cache_data
def load():
    files = {k: DATA / f"synthetic_{k}.csv" for k in ["projects", "milestones", "risks", "financials"]}
    if all(f.exists() for f in files.values()):
        dates = {"projects": ["start", "end"], "milestones": ["due", "forecast"], "risks": [], "financials": ["month"]}
        d = {k: pd.read_csv(f, parse_dates=dates[k]) for k, f in files.items()}
    else:
        d = generate(str(AS_OF.date()))
    return metrics.add_performance(d["projects"]), d["milestones"], metrics.add_risk_scores(d["risks"]), d["financials"]


projects_all, milestones_all, risks_all, fin_all = load()

ui.sidebar_brand("PMO Portfolio", f"Status date {AS_OF:%d %b %Y}")
st.sidebar.markdown("---")
objs = st.sidebar.multiselect("Strategic objectives", list(config.STRATEGIC_OBJECTIVES),
                              default=list(config.STRATEGIC_OBJECTIVES),
                              format_func=lambda k: f"{k} · {config.STRATEGIC_OBJECTIVES[k]}")
rag_sel = st.sidebar.multiselect("RAG status", ["Green", "Amber", "Red"], default=["Green", "Amber", "Red"])
st.sidebar.markdown("---")
st.sidebar.markdown("**RAG rules**  \nGreen: SPI & CPI ≥ 0.95  \nAmber: ≥ 0.85  \nRed: < 0.85")

projects = projects_all[projects_all["objective_id"].isin(objs) & projects_all["overall_rag"].isin(rag_sel)]
ids = set(projects["project_id"])
milestones = milestones_all[milestones_all["project_id"].isin(ids)]
risks = risks_all[risks_all["project_id"].isin(ids)]
fin = fin_all[fin_all["project_id"].isin(ids)]

ui.hero("PMO Portfolio & Strategy Execution Tracker",
        "Strategic objectives, projects, milestones, risks and spend in one view for a health-transformation PMO.",
        ["Strategy alignment", "Earned value & RAG", "Project drill-down", "Risk heatmap", "Budget vs actual",
         "Prioritisation", "Scenario planning", "Synthetic data"])

if projects.empty:
    st.warning("No projects match the filters.")
    st.stop()

s = metrics.portfolio_summary(projects, risks, milestones)
c = st.columns(6)
ui.kpi(c[0], "Projects", f"{s['projects']}", f"{len(set(projects['programme']))} programmes · {len(objs)} objectives")
ui.kpi(c[1], "Portfolio budget", f"SAR {s['budget_sar'] / 1e6:.1f}m", f"spent SAR {s['actual_cost_sar'] / 1e6:.1f}m")
ui.kpi(c[2], "Schedule index (SPI)", f"{s['portfolio_spi']:.2f}", "earned / planned value",
       ui.status_for(s["portfolio_spi"], 0.95, 0.85))
ui.kpi(c[3], "Cost index (CPI)", f"{s['portfolio_cpi']:.2f}", "earned value / actual cost",
       ui.status_for(s["portfolio_cpi"], 0.95, 0.85))
ui.kpi(c[4], "Open risks", f"{s['open_risks']}", f"{s['high_critical_risks']} high / critical",
       "bad" if s["high_critical_risks"] > 5 else "warn")
ui.kpi(c[5], "Milestones", f"{s['milestones_complete_pct']:.0f}% done", f"{s['milestones_overdue']} overdue",
       "bad" if s["milestones_overdue"] > 8 else "warn")
st.write("")

tabs = st.tabs(["Executive summary", "Strategy alignment", "Projects & RAG", "Project drill-down", "Milestones",
                "Risk register", "Budget vs actual", "Prioritisation", "Scenario planning"])

with tabs[0]:
    ui.synthetic_banner()
    st.write("")
    l, m, r = st.columns([1, 1.4, 1.2])
    l.plotly_chart(charts.rag_donut(s["rag_counts"]), width="stretch")
    m.plotly_chart(charts.objective_bar(metrics.objective_rollup(projects)), width="stretch")
    with r:
        st.markdown("#### Executive highlights")
        red = projects[projects["overall_rag"] == "Red"].sort_values("spi")
        top_risks = risks[risks["status"] != "Closed"].sort_values("score", ascending=False).head(3)
        st.markdown(
            f"- **{s['rag_counts']['Green']}** projects on track, **{s['rag_counts']['Amber']}** at risk, "
            f"**{s['rag_counts']['Red']}** off track.\n"
            f"- Portfolio SPI **{s['portfolio_spi']:.2f}** and CPI **{s['portfolio_cpi']:.2f}**.\n"
            f"- **{s['milestones_overdue']}** overdue milestones need recovery plans.\n"
            f"- **{s['high_critical_risks']}** high/critical open risks for steering-committee review.")
        if len(red):
            st.markdown("**Needs attention:** " + ", ".join(red["project"].head(3)))
        st.markdown("**Top risks:**")
        for t in top_risks.itertuples():
            st.markdown(f"- `{t.risk_id}` {t.category} · score {t.score} ({t.band}) → _{t.mitigation}_")
    st.markdown("#### Decisions requested (template)")
    st.dataframe(pd.DataFrame({"Decision": ["Approve re-baseline for red projects", "Release contingency for top risk",
                                            "Confirm Q4 milestone priorities"],
                               "Owner": ["Steering committee", "Portfolio sponsor", "PMO lead"],
                               "Needed by": ["Next SteerCo", "Next SteerCo", "End of month"]}),
                 hide_index=True, width="stretch")

with tabs[1]:
    st.plotly_chart(charts.strategy_sunburst(projects), width="stretch")
    st.dataframe(metrics.objective_rollup(projects).style.format({"budget_sar": "SAR {:,.0f}", "avg_progress": "{:.0f}%",
                                                                  "spi": "{:.2f}"}), hide_index=True, width="stretch")

with tabs[2]:
    st.plotly_chart(charts.spi_cpi_scatter(projects), width="stretch")
    cols = ["project_id", "project", "objective_id", "programme", "phase", "sponsor_dept", "planned_pct", "actual_pct",
            "spi", "cpi", "schedule_rag", "cost_rag", "overall_rag", "budget_sar", "eac_sar"]
    color = {"Green": "background-color:#d8f0ec", "Amber": "background-color:#fbf0cf", "Red": "background-color:#f7d6da"}
    st.dataframe(projects[cols].style.map(lambda v: color.get(v, ""), subset=["schedule_rag", "cost_rag", "overall_rag"])
                 .format({"spi": "{:.2f}", "cpi": "{:.2f}", "budget_sar": "{:,.0f}", "eac_sar": "{:,.0f}"}),
                 hide_index=True, width="stretch")

with tabs[4]:
    st.plotly_chart(charts.milestone_gantt(projects, milestones, AS_OF), width="stretch")
    od = milestones[milestones["status"] == "Overdue"].merge(projects[["project_id", "project"]], on="project_id")
    st.markdown(f"#### Overdue milestones ({len(od)})")
    od = od.assign(due=pd.to_datetime(od["due"]).dt.strftime("%d %b %Y"),
                   forecast=pd.to_datetime(od["forecast"]).dt.strftime("%d %b %Y"))
    st.dataframe(od[["project", "milestone", "due", "forecast"]], hide_index=True, width="stretch")

with tabs[5]:
    l, r = st.columns([1, 1.3])
    l.plotly_chart(charts.risk_heatmap(metrics.risk_matrix(risks)), width="stretch")
    reg = risks.merge(projects[["project_id", "project"]], on="project_id").sort_values("score", ascending=False)
    band_c = {"Critical": "background-color:#f7d6da", "High": "background-color:#fde2cf",
              "Medium": "background-color:#fbf0cf", "Low": "background-color:#d8f0ec"}
    r.markdown("#### Risk register")
    r.dataframe(reg[["risk_id", "project", "category", "likelihood", "impact", "score", "band", "owner", "status",
                     "mitigation"]].style.map(lambda v: band_c.get(v, ""), subset=["band"]),
                hide_index=True, width="stretch", height=380)

with tabs[6]:
    st.plotly_chart(charts.budget_chart(metrics.budget_by_month(fin)), width="stretch")
    st.plotly_chart(charts.spend_race(metrics.spend_by_programme_month(fin, projects)), width="stretch")
    st.plotly_chart(charts.variance_bar(projects), width="stretch")

with tabs[3]:
    ids_sorted = projects.sort_values("project_id")
    sel = st.selectbox("Project", ids_sorted["project_id"],
                       format_func=lambda i: f"{i} · {ids_sorted.set_index('project_id').loc[i, 'project']}")
    p = projects.set_index("project_id").loc[sel]
    ui.section(p["project"], f"{p['programme']} · {p['objective_id']} {p['objective']} · sponsor: {p['sponsor_dept']} "
               f"· phase: {p['phase']}")
    c1, c2, c3, c4, c5 = st.columns(5)
    rag_status = {"Green": "good", "Amber": "warn", "Red": "bad"}
    ui.kpi(c1, "Overall RAG", p["overall_rag"], f"schedule {p['schedule_rag']} · cost {p['cost_rag']}",
           rag_status[p["overall_rag"]])
    ui.kpi(c2, "Progress", f"{p['actual_pct']:.0f}%", f"plan {p['planned_pct']:.0f}%",
           ui.status_for(p["actual_pct"] - p["planned_pct"], -2, -8))
    ui.kpi(c3, "SPI / CPI", f"{p['spi']:.2f} / {p['cpi']:.2f}", "earned value indices", rag_status[p["overall_rag"]])
    ui.kpi(c4, "Budget", f"SAR {p['budget_sar'] / 1e6:.1f}m", f"EAC SAR {p['eac_sar'] / 1e6:.1f}m", "info")
    ui.kpi(c5, "Timeline", f"{pd.Timestamp(p['start']):%b %Y}", f"to {pd.Timestamp(p['end']):%b %Y}", "info")
    st.write("")
    l, r = st.columns([1.2, 1])
    l.plotly_chart(charts.s_curve(metrics.project_s_curve(fin, sel), "Spend S-curve: planned vs actual"),
                   width="stretch")
    with r:
        st.markdown("##### Milestones")
        ms = milestones[milestones["project_id"] == sel][["milestone", "due", "forecast", "status"]].copy()
        for col in ["due", "forecast"]:
            ms[col] = pd.to_datetime(ms[col]).dt.strftime("%d %b %Y")
        st.dataframe(ms, hide_index=True, width="stretch")
        st.markdown("##### Risks")
        st.dataframe(risks[risks["project_id"] == sel][["risk_id", "category", "score", "band", "status", "mitigation"]]
                     .sort_values("score", ascending=False), hide_index=True, width="stretch")

with tabs[7]:
    ui.section("Portfolio prioritisation", "Adjust the criteria weights; the ranking updates immediately.")
    w1, w2, w3, w4 = st.columns(4)
    weights = {"strategic": w1.slider("Strategic benefit", 0, 10, 4), "delivery": w2.slider("Delivery performance", 0, 10, 3),
               "risk": w3.slider("Risk exposure (lower is better)", 0, 10, 2),
               "cost": w4.slider("Investment size (smaller is better)", 0, 10, 1)}
    ranked = metrics.priority_scores(projects, risks, weights)
    l, r = st.columns([1.3, 1])
    l.plotly_chart(charts.priority_bar(ranked), width="stretch")
    r.dataframe(ranked[["rank", "project", "objective_id", "priority_score", "overall_rag", "benefit_score"]],
                hide_index=True, width="stretch", height=500)
    st.download_button("Download ranking (CSV)", ranked.to_csv(index=False).encode(), "portfolio_ranking.csv")

with tabs[8]:
    ui.section("Recovery scenario", "What happens to cost and finish dates if performance on the remaining work improves?")
    a, b = st.columns(2)
    cpi_gain = a.slider("CPI improvement on remaining work", 0.0, 0.20, 0.05, 0.01)
    spi_gain = b.slider("SPI improvement on remaining work", 0.0, 0.20, 0.05, 0.01)
    sc = metrics.eac_scenario(projects, cpi_gain, spi_gain)
    base_eac, new_eac = sc["baseline_eac_sar"].sum(), sc["scenario_eac_sar"].sum()
    k1, k2, k3, k4 = st.columns(4)
    ui.kpi(k1, "Baseline EAC", f"SAR {base_eac / 1e6:.1f}m", f"budget SAR {sc['budget_sar'].sum() / 1e6:.1f}m", "info")
    ui.kpi(k2, "Scenario EAC", f"SAR {new_eac / 1e6:.1f}m", f"saves SAR {(base_eac - new_eac) / 1e6:.1f}m",
           "good" if new_eac <= sc["budget_sar"].sum() else "warn")
    ui.kpi(k3, "Avg schedule slip", f"{sc['scenario_slip_days'].mean():.0f} days",
           f"baseline {sc['baseline_slip_days'].mean():.0f} days", "info")
    red_after = int((sc[["spi", "cpi"]].add([spi_gain, cpi_gain]).min(axis=1) < 0.85).sum())
    ui.kpi(k4, "Red projects", f"{red_after}", f"from {int((sc['overall_rag'] == 'Red').sum())} today",
           "good" if red_after == 0 else "warn")
    st.write("")
    st.plotly_chart(charts.scenario_eac_bar(sc), width="stretch")
    st.caption("EAC = AC + (BAC − EV) / future CPI. Schedule slip = planned duration / future SPI − planned duration.")

ui.footer()
