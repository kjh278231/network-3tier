from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_loader import load_failed_run
from agent import run_diagnosis


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose infeasibility of a failed network optimization run."
    )
    parser.add_argument("run_dir", help="Path to failed run directory (must contain input.json)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output markdown file path (default: diagnosis_<timestamp>.md in this directory)",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.exists():
        print(f"Error: run_dir does not exist: {run_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading failed run from: {run_dir}")
    run_data = load_failed_run(run_dir)

    nd = run_data.network_data
    print(
        f"Loaded: {nd.simulation.simulation_name} | "
        f"warehouses={len(nd.warehouses)} plants={len(nd.plants)} customers={len(nd.customers)}"
    )
    print("Running infeasibility diagnosis agent...")

    report = run_diagnosis(run_data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = (
        Path(args.output)
        if args.output
        else Path(__file__).parent / f"diagnosis_{timestamp}.md"
    )
    out_path.write_text(report, encoding="utf-8")
    print(f"\nDiagnosis report saved: {out_path}")


if __name__ == "__main__":
    main()
