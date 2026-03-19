from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class RunStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def list_run_dirs(self) -> list[Path]:
        return sorted([path for path in self.root.iterdir() if path.is_dir()], reverse=True)

    def create_run_dir(self) -> tuple[str, Path]:
        run_id = f"run_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        run_dir = self.root / run_id
        suffix = 1
        while run_dir.exists():
            run_id = f"run_{datetime.now().strftime('%Y%m%d%H%M%S')}_{suffix}"
            run_dir = self.root / run_id
            suffix += 1
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_id, run_dir

    def run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def exists(self, run_id: str) -> bool:
        return self.run_dir(run_id).exists()

    def meta_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "meta.json"

    def validation_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "validation.json"

    def input_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "input.json"

    def summary_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "summary.json"

    def cases_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "cases.json"

    def case_path(self, run_id: str, case_name: str) -> Path:
        return self.run_dir(run_id) / "cases" / f"{case_name}.json"

    def events_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "events.jsonl"

    def input_file_path(self, run_id: str, original_name: str) -> Path:
        return self.run_dir(run_id) / original_name

    def save_json(self, path: Path, payload: dict | list) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_json(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def append_event(self, run_id: str, level: str, message: str) -> None:
        payload = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "level": level,
            "message": message,
        }
        path = self.events_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def load_events(self, run_id: str) -> list[dict]:
        path = self.events_path(run_id)
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

