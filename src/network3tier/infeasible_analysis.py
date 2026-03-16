from __future__ import annotations

import json
from pathlib import Path


def write_engine_infeasible_analysis_context(
    run_dir: Path,
    *,
    case_name: str,
    case_type: str,
    solver_name: str,
    executable_ir_path: str,
) -> Path:
    payload = {
        "analysis_trigger": "engine_infeasible_only",
        "case_name": case_name,
        "case_type": case_type,
        "solver_name": solver_name,
        "precheck_fail_fast": False,
        "executable_ir_path": executable_ir_path,
        "schema_path": "docs/executable_ir_schema.json",
        "experiment_catalog_path": "docs/infeasible_experiment_catalog.md",
        "notes": [
            "This context is generated only when the engine runs and returns INFEASIBLE.",
            "Precheck fail-fast cases must not trigger LLM infeasibility analysis.",
            "The executable IR is the baseline artifact for submodel experiments."
        ],
    }
    path = run_dir / "engine_infeasible_analysis_context.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
