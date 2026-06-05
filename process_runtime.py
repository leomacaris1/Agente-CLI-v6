import atexit
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


class ProcessRuntimeTracker:
    def __init__(self, state_file: Path, pid_file: Path, process_name: str):
        self.state_file = Path(state_file)
        self.pid_file = Path(pid_file)
        self.process_name = process_name
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        atexit.register(self.mark_stopped)

    def load_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def start(self, **updates: Any) -> None:
        now = utc_now()
        pid = os.getpid()
        self.pid_file.write_text(f"{pid}\n", encoding="utf-8")
        state = self.load_state()
        state.update(
            {
                "process_name": self.process_name,
                "pid": pid,
                "started_at": state.get("started_at", now),
                "last_checked_at": now,
                "heartbeat_at": now,
                "status": "running",
            }
        )
        state.update(updates)
        self._write_state(state)

    def heartbeat(self, **updates: Any) -> None:
        now = utc_now()
        state = self.load_state()
        state.update(
            {
                "process_name": self.process_name,
                "pid": os.getpid(),
                "last_checked_at": now,
                "heartbeat_at": now,
                "status": "running",
            }
        )
        state.update(updates)
        self._write_state(state)

    def record_error(self, error: str, **updates: Any) -> None:
        self.heartbeat(last_error_at=utc_now(), last_error=str(error), status="error", **updates)

    def mark_stopped(self) -> None:
        state = self.load_state()
        if state:
            state.update(
                {
                    "process_name": self.process_name,
                    "pid": os.getpid(),
                    "last_checked_at": utc_now(),
                    "stopped_at": utc_now(),
                    "status": "stopped",
                }
            )
            self._write_state(state)
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except OSError:
            pass

    def _write_state(self, state: dict[str, Any]) -> None:
        self.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
