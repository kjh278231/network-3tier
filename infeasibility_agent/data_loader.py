from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from network3tier.domain import NetworkData
from network3tier.loader import load_network_data_from_payload


@dataclass
class FailedRunData:
    run_dir: Path
    network_data: NetworkData
    error_message: str
    solver: str


def load_failed_run(run_dir: Path) -> FailedRunData:
    run_dir = Path(run_dir).resolve()
    input_json = run_dir / "input.json"
    if not input_json.exists():
        raise FileNotFoundError(f"input.json not found in {run_dir}")

    payload = json.loads(input_json.read_text(encoding="utf-8"))
    network_data = load_network_data_from_payload(payload)

    error_message = ""
    solver = "SCIP"

    meta_path = run_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        error_message = meta.get("errorSummary", "")
        solver = meta.get("solver", "SCIP")
    else:
        error_txt = run_dir / "error.txt"
        if error_txt.exists():
            error_message = error_txt.read_text(encoding="utf-8").strip()

    return FailedRunData(
        run_dir=run_dir,
        network_data=network_data,
        error_message=error_message,
        solver=solver,
    )
