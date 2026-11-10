"""Plotly figures for the PMO tracker."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from .ui import AMBER, NAVY, PALETTE, RED, SKY, TEAL

pio.templates["navy"] = go.layout.Template(pio.templates["plotly_white"])
pio.templates["navy"].layout.colorway = PALETTE
pio.templates["navy"].layout.font = dict(family="Inter, Segoe UI, sans-serif", color=NAVY)
TEMPLATE = "navy"
RAG_COLORS = {"Green": TEAL, "Amber": AMBER, "Red": RED}


def rag_donut(counts: dict) -> go.Figure:
    fig = go.Figure(go.Pie(labels=list(counts), values=list(counts.values()), hole=0.62,
                           marker=dict(colors=[RAG_COLORS[k] for k in counts]), sort=False,
                           textinfo="value+label"))
    fig.update_layout(template=TEMPLATE, title="Overall RAG status", height=340, margin=dict(t=60, b=10),
                      showlegend=False,
                      annotations=[dict(text=f"<b>{sum(counts.values())}</b><br>projects", showarrow=False,
                                        font=dict(size=16, color=NAVY))])
    return fig


def strategy_sunburst(projects: pd.DataFrame) -> go.Figure:
    df = projects.assign(objective_label=projects["objective_id"] + " " + projects["objective"])
    fig = px.sunburst(df, path=["objective_label", "programme", "project"], values="budget_sar",
                      color="overall_rag", color_discrete_map={**RAG_COLORS, "(?)": SKY})
    fig.update_traces(insidetextorientation="radial")
    fig.update_layout(template=TEMPLATE, title="Strategy → programme → project (sized by budget, coloured by RAG)",
                      height=560, margin=dict(t=60, l=0, r=0, b=0))
    return fig


def objective_bar(rollup: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(y=rollup["objective_id"] + " " + rollup["objective"], x=rollup["avg_progress"],
                           orientation="h", marker_color=[RAG_COLORS[r] for r in rollup["rag"]],
                           text=rollup["avg_progress"].round(0).astype(int).astype(str) + "%", textposition="outside"))
    fig.update_layout(template=TEMPLATE, title="Average delivery progress by strategic objective",
                      xaxis=dict(range=[0, 110], title="% complete"), height=380, margin=dict(t=60, l=10))
    fig.update_yaxes(autorange="reversed")
    return fig


def spi_cpi_scatter(projects: pd.DataFrame) -> go.Figure:
    fig = px.scatter(projects, x="spi", y="cpi", size="budget_sar", color="overall_rag", hover_name="project",
                     color_discrete_map=RAG_COLORS, size_max=38)
    fig.add_vline(x=1, line_dash="dot", line_color=NAVY)
    fig.add_hline(y=1, line_dash="dot", line_color=NAVY)
    fig.add_annotation(x=1.08, y=1.12, text="Ahead & under budget", showarrow=False, font=dict(color=TEAL))
    fig.add_annotation(x=0.75, y=0.76, text="Behind & over budget", showarrow=False, font=dict(color=RED))
    fig.update_layout(template=TEMPLATE, title="Schedule (SPI) vs cost (CPI) performance",
                      xaxis_title="SPI (earned / planned value)", yaxis_title="CPI (earned value / actual cost)",
                      height=440, margin=dict(t=60))
    return fig


def milestone_gantt(projects: pd.DataFrame, milestones: pd.DataFrame, as_of: pd.Timestamp) -> go.Figure:
    df = projects.sort_values("start")
    fig = px.timeline(df, x_start="start", x_end="end", y="project", color="overall_rag",
                      color_discrete_map=RAG_COLORS, hover_data=["programme", "actual_pct"])
    ms = milestones.merge(df[["project_id", "project"]], on="project_id")
    sym = {"Complete": "diamond", "Overdue": "x", "Planned": "circle-open"}
    col = {"Complete": NAVY, "Overdue": RED, "Planned": "#495057"}
    for status, g in ms.groupby("status"):
        fig.add_scatter(x=g["forecast"], y=g["project"], mode="markers", name=f"Milestone: {status}",
                        marker=dict(symbol=sym[status], size=9, color=col[status], line=dict(width=1.5, color=col[status])),
                        text=g["milestone"], hovertemplate="%{y}<br>%{text}<br>%{x|%d %b %Y}<extra></extra>")
    fig.add_vline(x=as_of, line_dash="dash", line_color=NAVY)
    fig.add_annotation(x=as_of, y=1.0, yref="paper", yshift=14, text="Status date", showarrow=False, font=dict(color=NAVY), bgcolor="#ffffff")
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_layout(template=TEMPLATE, title="Project timeline and milestones", height=max(420, 26 * len(df)),
                      margin=dict(t=60), legend=dict(orientation="h", y=-0.08))
    return fig


def risk_heatmap(matrix: pd.DataFrame) -> go.Figure:
    import numpy as np
    sev = np.outer(np.arange(5, 0, -1), np.arange(1, 6))
    colorscale = [[0, "#cfe8e3"], [0.2, "#a7d7c5"], [0.4, AMBER], [0.65, "#f4a261"], [1, RED]]
    fig = go.Figure(go.Heatmap(z=sev, x=[f"L{i}" for i in range(1, 6)], y=[f"I{i}" for i in range(5, 0, -1)],
                               colorscale=colorscale, showscale=False, text=matrix.values,
                               texttemplate="<b>%{text}</b>", textfont=dict(size=18, color=NAVY),
                               hovertemplate="Impact %{y} × Likelihood %{x}<br>Open risks: %{text}<extra></extra>"))
    fig.update_layout(template=TEMPLATE, title="Open risk heatmap (count of risks)", height=420,
                      xaxis_title="Likelihood →", yaxis_title="Impact →", margin=dict(t=60))
    fig.update_yaxes(autorange="reversed")  # row 0 = impact 5, shown at the top
    return fig


def budget_chart(monthly: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=monthly["month"], y=monthly["planned_sar"] / 1e6, name="Planned (monthly)", marker_color=SKY)
    fig.add_bar(x=monthly["month"], y=monthly["actual_sar"] / 1e6, name="Actual (monthly)", marker_color=NAVY)
    fig.add_scatter(x=monthly["month"], y=monthly["cum_planned"] / 1e6, name="Cumulative planned", yaxis="y2",
                    line=dict(color=TEAL, width=3, dash="dot"))
    fig.add_scatter(x=monthly["month"], y=monthly["cum_actual"] / 1e6, name="Cumulative actual", yaxis="y2",
                    line=dict(color=AMBER, width=3))
    fig.update_layout(template=TEMPLATE, title="Budget vs actual spend (SAR millions)", barmode="group", height=420,
                      yaxis=dict(title="Monthly (SAR m)"), yaxis2=dict(title="Cumulative (SAR m)", overlaying="y",
                                                                       side="right", showgrid=False),
                      legend=dict(orientation="h", y=-0.15), margin=dict(t=60))
    return fig


def variance_bar(projects: pd.DataFrame) -> go.Figure:
    d = projects.sort_values("variance_at_completion_sar")
    fig = go.Figure(go.Bar(x=d["variance_at_completion_sar"] / 1e6, y=d["project"], orientation="h",
                           marker_color=[TEAL if v >= 0 else RED for v in d["variance_at_completion_sar"]]))
    fig.update_layout(template=TEMPLATE, title="Forecast variance at completion (budget − EAC, SAR m)",
                      height=max(420, 22 * len(d)), margin=dict(t=60), xaxis_title="SAR millions")
    return fig


def spend_race(t: pd.DataFrame) -> go.Figure:
    d = t.copy()
    d["month_label"] = pd.to_datetime(d["month"]).dt.strftime("%Y-%m")
    d["cum_m"] = d["cum_actual_sar"] / 1e6
    fig = px.bar(d, x="cum_m", y="programme", color="objective_id", orientation="h", animation_frame="month_label",
                 range_x=[0, d["cum_m"].max() * 1.12], color_discrete_sequence=PALETTE,
                 labels={"cum_m": "Cumulative actual spend (SAR m)", "programme": "", "objective_id": "Objective",
                         "month_label": "Month"})
    fig.update_layout(template=TEMPLATE, title="Cumulative spend by programme · press ▶ to replay the portfolio",
                      height=520, margin=dict(t=60), yaxis=dict(categoryorder="total ascending"))
    if fig.layout.updatemenus:
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 600
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 350
    return fig


def s_curve(f: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=f["month"], y=f["cum_planned"] / 1e6, name="Planned", line=dict(color=SKY, width=3, dash="dot"))
    fig.add_scatter(x=f["month"], y=f["cum_actual"] / 1e6, name="Actual", line=dict(color=NAVY, width=3),
                    fill="tonexty", fillcolor="rgba(141,169,196,.15)")
    fig.update_layout(template=TEMPLATE, title=title, height=320, yaxis_title="SAR m (cumulative)",
                      legend=dict(orientation="h", y=1.15), margin=dict(t=60))
    return fig


def scenario_eac_bar(df: pd.DataFrame) -> go.Figure:
    d = df.assign(delta=(df["baseline_eac_sar"] - df["scenario_eac_sar"]) / 1e6).sort_values("delta").tail(12)
    fig = go.Figure(go.Bar(x=d["delta"], y=d["project"], orientation="h", marker_color=TEAL,
                           text=d["delta"].round(2), textposition="outside"))
    fig.update_layout(template=TEMPLATE, title="Largest forecast savings under the scenario (SAR m)", height=420,
                      margin=dict(t=60), xaxis_title="Baseline EAC − scenario EAC (SAR m)")
    return fig


def priority_bar(df: pd.DataFrame, top: int = 15) -> go.Figure:
    d = df.head(top).iloc[::-1]
    fig = go.Figure()
    for col, color, name in [("strategic_contrib", NAVY, "Strategic"), ("delivery_contrib", TEAL, "Delivery"),
                             ("risk_contrib", AMBER, "Risk"), ("cost_contrib", SKY, "Cost")]:
        fig.add_bar(x=d[col], y=d["project"], orientation="h", name=name, marker_color=color)
    fig.add_scatter(x=d["priority_score"], y=d["project"], mode="markers+text", text=d["priority_score"],
                    textposition="middle right", marker=dict(color=RED, size=9, symbol="diamond"), name="Weighted score")
    fig.update_layout(template=TEMPLATE, barmode="stack", height=520, margin=dict(t=60),
                      title=f"Top {top} projects by weighted priority score", xaxis=dict(title="Score (0–100), split by criterion", range=[0, 105]),
                      legend=dict(orientation="h", y=1.08))
    return fig
