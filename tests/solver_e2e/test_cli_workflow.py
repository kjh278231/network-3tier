from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.network3tier.loader import load_network_data, load_network_data_from_json
from src.network3tier.optimizer import solve_case
from tests.test_support import build_input_json, build_workbook


REPO_ROOT = Path(__file__).resolve().parents[2]


class SolverCliE2ETest(unittest.TestCase):
    def test_excel_and_json_inputs_produce_identical_best_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            workbook_path = build_workbook(temp_root / "valid.xlsx")
            json_path = build_input_json(temp_root / "input.json")

            excel_case = solve_case(load_network_data(workbook_path), "CBC", "best_model", "best")
            json_case = solve_case(load_network_data_from_json(json_path), "CBC", "best_model", "best")

            self.assertEqual(excel_case.case_name, json_case.case_name)
            self.assertEqual(excel_case.selected_warehouses, json_case.selected_warehouses)
            self.assertEqual(excel_case.total_cost, json_case.total_cost)
            self.assertEqual(
                float(excel_case.summary.iloc[0]["Optimal Total Inbound Qty"]),
                float(json_case.summary.iloc[0]["Optimal Total Inbound Qty"]),
            )

    def test_cli_happy_path_writes_ranked_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            input_path = build_input_json(temp_root / "input.json")
            output_root = temp_root / "output"

            completed = subprocess.run(
                [
                    sys.executable,
                    "network_optimizer.py",
                    "--input",
                    str(input_path),
                    "--output-root",
                    str(output_root),
                    "--solver",
                    "CBC",
                    "--max-samples",
                    "2",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads(completed.stdout.strip().splitlines()[-1])
            self.assertEqual(summary["case_count"], 3)
            self.assertEqual(summary["required_warehouse_qty"], 2)

            run_dir = Path(summary["run_dir"])
            self.assertTrue((run_dir / "run_summary.json").exists())
            self.assertTrue((run_dir / "input.json").exists())
            self.assertTrue((run_dir / "output_summary.xls").exists())
            self.assertTrue((run_dir / "output_case1.xls").exists())
            self.assertTrue((run_dir / "output_case2.xls").exists())
            self.assertTrue((run_dir / "output_case3.xls").exists())

    def test_cli_invalid_input_fails_and_records_error_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            input_path = build_workbook(temp_root / "invalid.xlsx", scenario="demand_exceeds_supply")
            output_root = temp_root / "output"

            completed = subprocess.run(
                [
                    sys.executable,
                    "network_optimizer.py",
                    "--input",
                    str(input_path),
                    "--output-root",
                    str(output_root),
                    "--solver",
                    "CBC",
                    "--max-samples",
                    "1",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            run_dirs = sorted(path for path in output_root.iterdir() if path.is_dir())
            self.assertEqual(len(run_dirs), 1)
            error_text = (run_dirs[0] / "error.txt").read_text(encoding="utf-8")
            self.assertIn("Total Do Qty (100.0) exceeds plant Product Qty (80.0).", error_text)


if __name__ == "__main__":
    unittest.main()
