from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from ..loader import load_network_data, validate_network_data
from ..logging_utils import get_logger
from ..optimizer import solve_case
from ..ranking import build_summary_workbook
from ..sampling import sample_neighboring_warehouse_sets
from .serializers import build_case_payload, build_input_payload, case_summary_row
from .storage import RunStorage


LOGGER = get_logger()


def build_validation_issues(exc: Exception) -> list[dict]:
    messages = [line.strip() for line in str(exc).splitlines() if line.strip()]
    issues = []
    for idx, message in enumerate(messages, start=1):
        issues.append(
            {
                "issueId": f"validation_{idx:03d}",
                "severity": "error",
                "ruleCode": "VALIDATION_ERROR",
                "ruleName": "Input validation error",
                "message": message,
                "recommendation": None,
                "affectedEntityType": "unknown",
                "affectedCount": 1,
                "affectedRefs": [],
                "blocking": True,
            }
        )
    return issues


class RunService:
    def __init__(self, storage: RunStorage):
        self.storage = storage

    def create_run(
        self,
        source_file: Path,
        original_name: str,
        solver: str,
        max_samples: int,
        random_seed: int,
    ) -> dict:
        run_id, _run_dir = self.storage.create_run_dir()
        destination = self.storage.input_file_path(run_id, original_name)
        shutil.copy2(source_file, destination)
        now = datetime.now().astimezone().isoformat()
        meta = {
            "runId": run_id,
            "status": "uploaded",
            "inputFileName": original_name,
            "createdAt": now,
            "updatedAt": now,
            "solver": solver,
            "maxSamples": max_samples,
            "randomSeed": random_seed,
            "caseCount": 0,
            "bestCaseName": None,
            "bestTotalCost": None,
            "bestTotalInboundQty": None,
            "requiredWarehouseQty": None,
            "errorSummary": None,
        }
        self.storage.save_json(self.storage.meta_path(run_id), meta)
        self.storage.append_event(run_id, "INFO", f"Run created from file '{original_name}'")
        return meta

    def _load_meta(self, run_id: str) -> dict:
        path = self.storage.meta_path(run_id)
        if not path.exists():
            raise FileNotFoundError(run_id)
        return self.storage.load_json(path)

    def _save_meta(self, run_id: str, meta: dict) -> None:
        meta["updatedAt"] = datetime.now().astimezone().isoformat()
        self.storage.save_json(self.storage.meta_path(run_id), meta)

    def get_run(self, run_id: str) -> dict:
        meta = self._load_meta(run_id)
        simulation = None
        input_payload_path = self.storage.input_path(run_id)
        if input_payload_path.exists():
            input_payload = self.storage.load_json(input_payload_path)
            sim_rows = input_payload.get("simulation", [])
            simulation = sim_rows[0] if sim_rows else None
        return {"run": meta, "simulation": simulation}

    def list_runs(self) -> list[dict]:
        runs = []
        for run_dir in self.storage.list_run_dirs():
            path = run_dir / "meta.json"
            if path.exists():
                runs.append(self.storage.load_json(path))
        return runs

    def _input_file_for_run(self, run_id: str, meta: dict) -> Path:
        return self.storage.input_file_path(run_id, meta["inputFileName"])

    def validate_run(self, run_id: str) -> dict:
        meta = self._load_meta(run_id)
        meta["status"] = "validating"
        self._save_meta(run_id, meta)
        self.storage.append_event(run_id, "INFO", "Validation started")
        input_file = self._input_file_for_run(run_id, meta)
        try:
            data = load_network_data(input_file)
            validate_network_data(data)
            input_payload = build_input_payload(data)
            self.storage.save_json(self.storage.input_path(run_id), input_payload)
            validation = {
                "summary": {"errorCount": 0, "warningCount": 0, "infoCount": 0, "blocking": False},
                "issues": [],
            }
            self.storage.save_json(self.storage.validation_path(run_id), validation)
            meta["status"] = "ready"
            meta["requiredWarehouseQty"] = data.simulation.warehouse_qty
            meta["errorSummary"] = None
            self._save_meta(run_id, meta)
            self.storage.append_event(run_id, "INFO", "Validation completed successfully")
            return {"runId": run_id, "status": meta["status"], **validation}
        except Exception as exc:
            issues = build_validation_issues(exc)
            validation = {
                "summary": {
                    "errorCount": len(issues),
                    "warningCount": 0,
                    "infoCount": 0,
                    "blocking": True,
                },
                "issues": issues,
            }
            self.storage.save_json(self.storage.validation_path(run_id), validation)
            meta["status"] = "validation_failed"
            meta["errorSummary"] = str(exc)
            self._save_meta(run_id, meta)
            self.storage.append_event(run_id, "ERROR", f"Validation failed: {exc}")
            return {"runId": run_id, "status": meta["status"], **validation}

    def get_validation(self, run_id: str) -> dict:
        path = self.storage.validation_path(run_id)
        if not path.exists():
            return {"summary": {"errorCount": 0, "warningCount": 0, "infoCount": 0, "blocking": False}, "issues": []}
        return self.storage.load_json(path)

    def execute_run(self, run_id: str) -> None:
        meta = self._load_meta(run_id)
        if meta["status"] not in {"ready", "completed"}:
            raise RuntimeError(f"Run '{run_id}' is not ready for execution.")
        meta["status"] = "running"
        meta["errorSummary"] = None
        self._save_meta(run_id, meta)
        self.storage.append_event(run_id, "INFO", "Execution started")
        input_file = self._input_file_for_run(run_id, meta)
        try:
            data = load_network_data(input_file)
            validate_network_data(data)
            best_case = solve_case(data, meta["solver"], "best_model", "best")
            cases = [best_case]
            locked_warehouse_ids = set(data.customers["Mapping ID"].dropna().astype(str)) if "Mapping ID" in data.customers.columns else set()
            sampled_sets = sample_neighboring_warehouse_sets(
                active_warehouse_ids=data.warehouses["Warehouse ID"].tolist(),
                base_set=set(best_case.selected_warehouses),
                locked_warehouse_ids=locked_warehouse_ids,
                max_samples=max(meta["maxSamples"] * 10, meta["maxSamples"]),
                random_seed=meta["randomSeed"],
            )
            sampled_success_count = 0
            for idx, warehouse_set in enumerate(sampled_sets, start=1):
                if sampled_success_count >= meta["maxSamples"]:
                    break
                case_name = f"sampled_case_{idx}"
                try:
                    case_result = solve_case(
                        data,
                        meta["solver"],
                        case_name,
                        "designated",
                        forced_open_warehouses=warehouse_set,
                    )
                except RuntimeError as exc:
                    self.storage.append_event(run_id, "ERROR", f"Skipping infeasible sampled case '{case_name}': {exc}")
                    continue
                cases.append(case_result)
                sampled_success_count += 1
            summary_df = build_summary_workbook(cases)
            summary_lookup = summary_df.set_index("Case Name")
            for case in cases:
                case.summary = summary_lookup.loc[[case.case_name]].reset_index()
            summary_rows = [case_summary_row(case) for case in cases]
            cases_payload = [
                {
                    "caseName": row["caseName"],
                    "caseType": row["caseType"],
                    "totalRank": row["totalRank"],
                    "optimalCost": row["optimalCost"],
                }
                for row in summary_rows
            ]
            self.storage.save_json(self.storage.summary_path(run_id), {"rows": summary_rows})
            self.storage.save_json(self.storage.cases_path(run_id), {"cases": cases_payload})
            for case in cases:
                self.storage.save_json(self.storage.case_path(run_id, case.case_name), build_case_payload(case, data))
            meta["status"] = "completed"
            meta["caseCount"] = len(cases)
            meta["bestCaseName"] = best_case.case_name
            meta["bestTotalCost"] = best_case.total_cost
            meta["bestTotalInboundQty"] = float(best_case.summary.iloc[0]["Optimal Total Inbound Qty"])
            meta["requiredWarehouseQty"] = data.simulation.warehouse_qty
            self._save_meta(run_id, meta)
            self.storage.append_event(run_id, "INFO", "Execution completed successfully")
        except Exception as exc:
            meta["status"] = "failed"
            meta["errorSummary"] = str(exc)
            self._save_meta(run_id, meta)
            self.storage.append_event(run_id, "ERROR", f"Execution failed: {exc}")
            raise
