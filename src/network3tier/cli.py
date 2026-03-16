from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .loader import (
    DataValidationError,
    get_customer_mapping_requirements,
    load_network_data,
    validate_network_data,
)
from .logging_utils import setup_logging
from .optimizer import solve_case
from .output import write_case_output, write_xls_workbook
from .ranking import build_summary_workbook
from .sampling import sample_neighboring_warehouse_sets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Optimize a plant-warehouse-customer network with OR-Tools."
    )
    parser.add_argument("--input", default="TRNS_DOWNLOAD_20260311081304.xls")
    parser.add_argument("--output-root", default="output")
    parser.add_argument("--solver", default="SCIP", choices=["SCIP", "CBC"])
    parser.add_argument("--max-samples", type=int, default=10)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "ERROR"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = Path(args.output_root) / datetime.now().strftime("%Y%m%d%H%M%S")
    logger = setup_logging(run_dir, args.log_level)
    logger.info("Run directory: %s", run_dir)
    logger.info("Starting optimization workflow")

    try:
        data = load_network_data(Path(args.input))
        validate_network_data(data)
        locked_warehouse_ids = set(get_customer_mapping_requirements(data).values())

        best_case = solve_case(data, args.solver, "best_model", "best")
        cases = [best_case]

        sampled_sets = sample_neighboring_warehouse_sets(
            active_warehouse_ids=data.warehouses["Warehouse ID"].tolist(),
            base_set=set(best_case.selected_warehouses),
            locked_warehouse_ids=locked_warehouse_ids,
            max_samples=max(args.max_samples * 10, args.max_samples),
            random_seed=args.random_seed,
        )

        sampled_success_count = 0
        for idx, warehouse_set in enumerate(sampled_sets, start=1):
            if sampled_success_count >= args.max_samples:
                break
            case_name = f"sampled_case_{idx}"
            try:
                case_result = solve_case(
                    data,
                    args.solver,
                    case_name,
                    "designated",
                    forced_open_warehouses=warehouse_set,
                )
            except RuntimeError as exc:
                logger.error("Skipping infeasible sampled case '%s': %s", case_name, exc)
                continue
            cases.append(case_result)
            sampled_success_count += 1

        summary_df = build_summary_workbook(cases)
        summary_lookup = summary_df.set_index("Case Name")
        for case in cases:
            case.summary = summary_lookup.loc[[case.case_name]].reset_index()

        for idx, case in enumerate(cases, start=1):
            path = write_case_output(run_dir, idx, case)
            logger.info("Saved case workbook: %s", path)

        summary_path = run_dir / "output_summary.xls"
        write_xls_workbook(summary_path, {"summary": summary_df})
        logger.info("Saved summary workbook: %s", summary_path)

        summary_json = {
            "run_dir": str(run_dir),
            "case_count": len(cases),
            "best_case": best_case.case_name,
            "best_total_cost": best_case.total_cost,
            "best_total_inbound_qty": float(best_case.summary.iloc[0]["Optimal Total Inbound Qty"]),
            "required_warehouse_qty": data.simulation.warehouse_qty,
        }
        (run_dir / "run_summary.json").write_text(
            json.dumps(summary_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Workflow completed successfully")
        print(json.dumps(summary_json, ensure_ascii=False))
    except Exception as exc:
        logger.error("Workflow failed: %s", exc)
        (run_dir / "error.txt").write_text(str(exc), encoding="utf-8")
        raise
