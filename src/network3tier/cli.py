from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from .infeasible_analysis import write_engine_infeasible_analysis_context
from .loader import DataValidationError, get_customer_mapping_requirements, load_network_data, validate_network_data
from .logging_utils import setup_logging
from .optimizer import OptimizationInfeasibleError, solve_case
from .output import write_case_output, write_xls_workbook
from .precheck import build_fail_case, precheck_issues_to_frame, run_precheck
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
        precheck_result = run_precheck(data)
        if precheck_result.fail_fast:
            fail_case = build_fail_case("best_model_precheck_fail", "fail_fast", precheck_result)
            summary_df = fail_case.summary.copy()
            case_path = write_case_output(run_dir, 1, fail_case)
            logger.error(
                "Precheck detected deterministic infeasibility. Solver execution skipped. issue_count=%d",
                len(precheck_result.issues),
            )
            logger.info("Saved fail-fast workbook: %s", case_path)
            summary_path = run_dir / "output_summary.xls"
            write_xls_workbook(summary_path, {"summary": summary_df, "precheckIssues": precheck_issues_to_frame(precheck_result)})
            summary_json = {
                "run_dir": str(run_dir),
                "run_status": "FAIL",
                "failed_before_solver": True,
                "precheck_issue_count": len(precheck_result.issues),
                "precheck_issue_ids": [issue.issue_id for issue in precheck_result.issues],
                "case_count": 1,
                "best_case": None,
                "best_total_cost": None,
                "required_warehouse_qty": data.simulation.warehouse_qty,
            }
            (run_dir / "run_summary.json").write_text(
                json.dumps(summary_json, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(json.dumps(summary_json, ensure_ascii=False))
            return
        locked_warehouse_ids = set(get_customer_mapping_requirements(data).values())

        try:
            best_case = solve_case(data, args.solver, "best_model", "best")
        except OptimizationInfeasibleError:
            context_path = write_engine_infeasible_analysis_context(
                run_dir,
                case_name="best_model",
                case_type="best",
                solver_name=args.solver,
                executable_ir_path="docs/best_model.exir.json",
            )
            logger.error(
                "Engine returned INFEASIBLE for best_model. Analysis context saved: %s",
                context_path,
            )
            raise
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
            "run_status": "SUCCESS",
            "failed_before_solver": False,
            "precheck_issue_count": 0,
            "precheck_issue_ids": [],
            "case_count": len(cases),
            "best_case": best_case.case_name,
            "best_total_cost": best_case.total_cost,
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
