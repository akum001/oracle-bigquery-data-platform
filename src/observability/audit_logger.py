import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class PipelineAuditLogger:
    def __init__(self, log_path: Path = Path("data/state/pipeline_audit_log.jsonl")) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = str(uuid.uuid4())[:12]
        self.started_at = datetime.now(timezone.utc)
        self._t0 = time.perf_counter()
        self.stages: Dict[str, Any] = {}

    def record_stage(self, stage_name: str, duration_sec: float, status: str, details: Dict[str, Any] | None = None) -> None:
        self.stages[stage_name] = {
            "status": status,
            "duration_sec": round(duration_sec, 4),
            "details": details or {},
        }

    def finalize(self, overall_status: str, error_message: str | None = None) -> Dict[str, Any]:
        total_duration = round(time.perf_counter() - self._t0, 4)
        event = {
            "run_id": self.run_id,
            "started_at_utc": self.started_at.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_duration_sec": total_duration,
            "status": overall_status,
            "error": error_message,
            "stages": self.stages,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        return event
