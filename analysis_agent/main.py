from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze network optimization results with an AI agent."
    )
    parser.add_argument("run_dir", help="Path to CLI output dir or web_run dir")
    parser.add_argument(
        "--output",
        default=None,
        help="Output markdown file path (default: report_<timestamp>.md in this directory)",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.exists():
        print(f"Error: run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Import here so errors surface clearly
    from data_loader import load_run
    from agent import run_analysis

    print(f"Loading run data from: {run_dir}")
    run_data = load_run(run_dir)
    print(
        f"Loaded {len(run_data.cases)} case(s) | "
        f"{len(run_data.warehouses)} warehouses | "
        f"{len(run_data.customers)} customers"
    )

    print("Running AI analysis agent...")
    report = run_analysis(run_data)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(args.output) if args.output else Path(__file__).parent / f"report_{timestamp}.md"
    out_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved: {out_path}")


if __name__ == "__main__":
    main()
