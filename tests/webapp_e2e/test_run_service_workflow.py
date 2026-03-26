from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.network3tier.loader import load_network_data, load_network_data_from_json
from src.network3tier.optimizer import solve_case
from src.network3tier.webapi.service import RunService
from src.network3tier.webapi.storage import RunStorage
from tests.test_support import build_workbook


class WebAppRunServiceE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temp_dir.name)
        self.storage = RunStorage(self.temp_root / "web_runs")
        self.service = RunService(self.storage)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_run_service_persists_full_web_app_lifecycle_outputs(self) -> None:
        workbook = build_workbook(self.temp_root / "valid.xlsx")
        baseline_case = solve_case(load_network_data(workbook), "CBC", "best_model", "best")
        meta = self.service.create_run(
            source_file=workbook,
            original_name="valid.xlsx",
            solver="CBC",
            max_samples=2,
            random_seed=42,
        )
        run_id = meta["runId"]

        listed_runs = self.service.list_runs()
        self.assertEqual(len(listed_runs), 1)
        self.assertEqual(listed_runs[0]["runId"], run_id)

        validation = self.service.validate_run(run_id)
        self.assertEqual(validation["status"], "ready")
        self.assertFalse(validation["summary"]["blocking"])

        run_snapshot = self.service.get_run(run_id)
        self.assertEqual(run_snapshot["run"]["status"], "ready")
        self.assertEqual(run_snapshot["simulation"]["warehouseQty"], 2)
        input_json_path = self.storage.input_path(run_id)
        json_case = solve_case(load_network_data_from_json(input_json_path), "CBC", "best_model", "best")
        self.assertEqual(baseline_case.selected_warehouses, json_case.selected_warehouses)
        self.assertEqual(baseline_case.total_cost, json_case.total_cost)
        self.assertEqual(
            float(baseline_case.summary.iloc[0]["Optimal Total Inbound Qty"]),
            float(json_case.summary.iloc[0]["Optimal Total Inbound Qty"]),
        )

        self.storage.input_file_path(run_id, "valid.xlsx").unlink()

        self.service.execute_run(run_id)

        final_run = self.service.get_run(run_id)
        self.assertEqual(final_run["run"]["status"], "completed")
        self.assertEqual(final_run["run"]["caseCount"], 3)
        self.assertEqual(final_run["run"]["bestCaseName"], "best_model")

        summary_payload = self.storage.load_json(self.storage.summary_path(run_id))
        self.assertEqual(len(summary_payload["rows"]), 3)

        cases_payload = self.storage.load_json(self.storage.cases_path(run_id))
        self.assertEqual(len(cases_payload["cases"]), 3)
        best_case_name = cases_payload["cases"][0]["caseName"]

        case_payload = self.storage.load_json(self.storage.case_path(run_id, best_case_name))
        self.assertIn("warehouseSummary", case_payload)
        self.assertEqual(len(case_payload["warehouseSummary"]), 2)
        self.assertIn("coverageDetails", case_payload)

        events = self.storage.load_events(run_id)
        self.assertTrue(any(item["message"] == "Validation completed successfully" for item in events))
        self.assertTrue(any(item["message"] == "Execution completed successfully" for item in events))

    def test_run_service_records_blocking_validation_issues_for_invalid_workbook(self) -> None:
        workbook = build_workbook(self.temp_root / "invalid.xlsx", scenario="demand_exceeds_supply")
        meta = self.service.create_run(
            source_file=workbook,
            original_name="invalid.xlsx",
            solver="CBC",
            max_samples=1,
            random_seed=7,
        )
        run_id = meta["runId"]

        validation = self.service.validate_run(run_id)
        self.assertEqual(validation["status"], "validation_failed")
        self.assertTrue(validation["summary"]["blocking"])
        self.assertGreaterEqual(validation["summary"]["errorCount"], 1)

        saved_validation = self.service.get_validation(run_id)
        self.assertTrue(saved_validation["summary"]["blocking"])
        self.assertIn("exceeds plant Product Qty", saved_validation["issues"][0]["message"])

        run_snapshot = self.service.get_run(run_id)
        self.assertEqual(run_snapshot["run"]["status"], "validation_failed")
        self.assertIn("exceeds plant Product Qty", run_snapshot["run"]["errorSummary"])


if __name__ == "__main__":
    unittest.main()
