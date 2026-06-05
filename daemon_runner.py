import json
import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from process_runtime import ProcessRuntimeTracker, utc_now


class DaemonRunner:
    def __init__(
        self,
        agent,
        state_dir: Path,
        logger: Optional[logging.Logger] = None,
        runtime_tracker: Optional[ProcessRuntimeTracker] = None,
    ):
        self.agent = agent
        self.state_dir = Path(state_dir).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "daemon_state.json"
        self.logger = logger or logging.getLogger("agent.daemon")
        self.runtime_tracker = runtime_tracker

    def status(self) -> str:
        state = self._load_state()
        return (
            "Daemon status\n"
            f"- Ciclos: {state.get('cycles', 0)}\n"
            f"- Ultimo ciclo: {state.get('last_cycle_at', 'nunca')}\n"
            f"- Ultima accion: {state.get('last_action', 'ninguna')}\n"
            f"- Ultimo resultado: {state.get('last_result', 'ninguno')}"
        )

    def run_once(self, project: Optional[str] = None, send_digest: bool = False) -> str:
        state = self._load_state()
        result = self.agent.queue_run_next(project=project)
        cycle_at = datetime.now().isoformat()
        state["cycles"] = state.get("cycles", 0) + 1
        state["last_cycle_at"] = cycle_at
        state["last_action"] = f"queue_run_next:{project or 'all'}"
        state["last_result"] = result[:1000]
        self._save_state(state)
        if self.runtime_tracker:
            self.runtime_tracker.heartbeat(
                last_cycle_at=cycle_at,
                last_action=state["last_action"],
                last_result=state["last_result"],
                cycles=state["cycles"],
                project=project or "all",
                last_digest_attempted=send_digest,
            )
        self.logger.info("Ciclo completado | proyecto=%s | digest=%s | resultado=%s", project or "all", send_digest, result)

        if send_digest:
            digest_result = self.agent.telegram_operator.send_message(self.agent.telegram_status())
            if self.runtime_tracker:
                self.runtime_tracker.heartbeat(last_digest_sent_at=utc_now(), last_digest_result=str(digest_result))
            self.logger.info("Digest enviado | resultado=%s", digest_result)

        return result

    def loop(self, interval_seconds: int = 300, project: Optional[str] = None, digest_every: int = 12):
        if self.runtime_tracker:
            self.runtime_tracker.start(
                interval_seconds=interval_seconds,
                digest_every=digest_every,
                project=project or "all",
            )
        self.logger.info(
            "Daemon iniciado | intervalo=%ss | proyecto=%s | digest_every=%s",
            interval_seconds,
            project or "all",
            digest_every,
        )
        while True:
            state = self._load_state()
            next_cycle = state.get("cycles", 0) + 1
            send_digest = digest_every > 0 and next_cycle % digest_every == 0
            try:
                result = self.run_once(project=project, send_digest=send_digest)
                self.logger.info("Resultado del ciclo | %s", result)
            except Exception as e:
                self._record_error(str(e))
                if self.runtime_tracker:
                    self.runtime_tracker.record_error(str(e), project=project or "all")
                self.logger.exception("Error daemon")
            time.sleep(interval_seconds)

    def _record_error(self, error: str):
        state = self._load_state()
        state["cycles"] = state.get("cycles", 0) + 1
        state["last_cycle_at"] = datetime.now().isoformat()
        state["last_action"] = "error"
        state["last_result"] = error[:1000]
        self._save_state(state)
        self.logger.error("Estado de error registrado | %s", error)

    def _load_state(self) -> Dict:
        if not self.state_file.exists():
            return {
                "cycles": 0,
                "created_at": datetime.now().isoformat(),
            }
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"cycles": 0, "created_at": datetime.now().isoformat()}

    def _save_state(self, state: Dict):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


def env_interval(default: int = 300) -> int:
    try:
        return int(os.getenv("AGENT_DAEMON_INTERVAL_SECONDS", str(default)))
    except ValueError:
        return default


def env_digest_every(default: int = 12) -> int:
    try:
        return int(os.getenv("AGENT_DAEMON_DIGEST_EVERY", str(default)))
    except ValueError:
        return default
