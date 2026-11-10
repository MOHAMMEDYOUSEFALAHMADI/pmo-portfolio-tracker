"""Generate synthetic PMO portfolio data. Usage: python scripts/generate_data.py --projects 24 --seed 15"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pmo_tracker.data import generate  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--as-of", default="2025-09-30")
    p.add_argument("--projects", type=int, default=24)
    p.add_argument("--seed", type=int, default=15)
    a = p.parse_args()
    d = generate(a.as_of, a.projects, a.seed)
    (ROOT / "data").mkdir(exist_ok=True)
    for k, df in d.items():
        df.to_csv(ROOT / "data" / f"synthetic_{k}.csv", index=False)
    print("Wrote synthetic " + ", ".join(f"{k} ({len(v)})" for k, v in d.items()))


if __name__ == "__main__":
    main()
