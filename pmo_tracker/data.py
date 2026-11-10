"""Synthetic portfolio generator: projects, milestones, risks and monthly financials. SYNTHETIC ONLY."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

_ADJ = ["Integrated", "Smart", "Regional", "Unified", "Rapid", "Enterprise", "Patient-centred", "Next-gen"]
_NOUN = ["Pathway", "Platform", "Programme", "Rollout", "Initiative", "Hub", "Framework", "Upgrade"]


def generate(as_of: str = "2025-09-30", n_projects: int = 24, seed: int = 15) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    as_of_ts = pd.Timestamp(as_of)
    projects, milestones, risks, fin = [], [], [], []
    so_keys = list(config.STRATEGIC_OBJECTIVES)
    for i in range(n_projects):
        so = so_keys[i % len(so_keys)]
        prog = rng.choice(config.PROGRAMMES[so])
        pid = f"PRJ-{i + 1:03d}"
        start = as_of_ts - pd.Timedelta(days=int(rng.integers(60, 540)))
        duration = int(rng.integers(240, 720))
        end = start + pd.Timedelta(days=duration)
        budget = float(rng.integers(8, 120)) * 100_000  # SAR
        planned_pct = float(np.clip((as_of_ts - start).days / duration, 0, 1))
        spi = float(np.clip(rng.normal(0.94, 0.11), 0.65, 1.12))
        cpi = float(np.clip(rng.normal(0.96, 0.09), 0.70, 1.15))
        actual_pct = float(np.clip(planned_pct * spi, 0, 1))
        ev = budget * actual_pct
        ac = ev / cpi
        phase = config.PHASES[min(int(actual_pct * 4.2) + (0 if actual_pct > 0.05 else 0), 4)]
        name = f"{rng.choice(_ADJ)} {prog.split()[0]} {rng.choice(_NOUN)}"
        projects.append(dict(project_id=pid, project=name, objective_id=so,
                             objective=config.STRATEGIC_OBJECTIVES[so], programme=prog,
                             sponsor_dept=rng.choice(config.DEPARTMENTS), phase=phase,
                             start=start, end=end, budget_sar=budget, planned_pct=round(planned_pct * 100, 1),
                             actual_pct=round(actual_pct * 100, 1), earned_value=ev, actual_cost=ac,
                             planned_value=budget * planned_pct, benefit_score=int(rng.integers(2, 6))))
        # milestones
        n_ms = int(rng.integers(4, 7))
        for k in range(n_ms):
            due = start + pd.Timedelta(days=int(duration * (k + 1) / (n_ms + 1)))
            done = due <= as_of_ts and rng.random() < 0.8 * spi
            slip = int(rng.integers(0, 45)) if (due <= as_of_ts and not done) or rng.random() < 0.25 else 0
            milestones.append(dict(project_id=pid, milestone=f"M{k + 1}: " + ["Business case", "Design sign-off",
                                   "Build complete", "Pilot go-live", "Scale-up", "Benefits review"][k],
                                   due=due, forecast=due + pd.Timedelta(days=slip),
                                   status="Complete" if done else ("Overdue" if due < as_of_ts else "Planned")))
        # risks
        for r in range(int(rng.integers(1, 5))):
            lik, imp = int(rng.integers(1, 6)), int(rng.integers(1, 6))
            risks.append(dict(risk_id=f"RSK-{len(risks) + 1:03d}", project_id=pid,
                              category=rng.choice(config.RISK_CATEGORIES), likelihood=lik, impact=imp,
                              owner=rng.choice(config.DEPARTMENTS),
                              status=rng.choice(["Open", "Open", "Mitigating", "Closed"]),
                              mitigation=rng.choice(["Re-baseline schedule", "Add vendor resources",
                                                     "Escalate to steering committee", "Phase scope",
                                                     "Contingency budget", "Stakeholder engagement plan"])))
        # monthly financials (planned vs actual spend)
        months = pd.date_range(start.to_period("M").to_timestamp(), as_of_ts, freq="MS")
        if len(months):
            plan_month = budget / max(duration / 30.4, 1)
            act_total = ac
            weights = rng.dirichlet(np.ones(len(months)) * 3)
            for mth, w in zip(months, weights):
                fin.append(dict(project_id=pid, month=mth, planned_sar=plan_month, actual_sar=act_total * w))
    return {"projects": pd.DataFrame(projects), "milestones": pd.DataFrame(milestones),
            "risks": pd.DataFrame(risks), "financials": pd.DataFrame(fin)}
