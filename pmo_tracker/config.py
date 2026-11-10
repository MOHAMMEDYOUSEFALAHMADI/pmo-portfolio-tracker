"""Strategic objectives, programmes and scoring rules.

Themes are illustrative and inspired by publicly described health-transformation
goals (Vision 2030-style). They are not an official framework or any organisation's plan.
"""

STRATEGIC_OBJECTIVES = {
    "SO1": "Improve access to healthcare services",
    "SO2": "Enhance quality and patient safety",
    "SO3": "Accelerate digital health and data",
    "SO4": "Strengthen prevention and population health",
    "SO5": "Develop the health workforce",
    "SO6": "Improve efficiency and value-based care",
}

PROGRAMMES = {
    "SO1": ["Virtual care expansion", "Emergency access improvement"],
    "SO2": ["Accreditation readiness", "Patient safety culture"],
    "SO3": ["EMR optimisation", "Analytics & BI platform"],
    "SO4": ["Chronic disease screening", "Community health outreach"],
    "SO5": ["Clinical leadership academy", "Workforce planning"],
    "SO6": ["Procurement savings", "Length-of-stay reduction"],
}

PHASES = ["Initiation", "Planning", "Execution", "Monitoring", "Closure"]
DEPARTMENTS = ["Clinical Operations", "Quality", "IT / Digital", "Public Health", "HR", "Finance", "Nursing"]
RISK_CATEGORIES = ["Schedule", "Budget", "Resource", "Technical", "Regulatory", "Stakeholder", "Vendor"]

# RAG thresholds on schedule (SPI) and cost (CPI) performance indices
RAG_RULES = {"green": 0.95, "amber": 0.85}
RISK_BANDS = {"Low": (1, 4), "Medium": (5, 9), "High": (10, 15), "Critical": (16, 25)}
