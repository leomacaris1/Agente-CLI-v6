import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


@dataclass
class PolicyDecision:
    level: str
    reason: str


class Governance:
    """Small permission layer for autonomous actions."""

    def __init__(self, state_dir: Optional[Path] = None):
        configured_dir = os.getenv("AGENT_STATE_DIR")
        self.state_dir = (state_dir or Path(configured_dir or ".agent_state")).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.actions_file = self.state_dir / "actions.jsonl"
        self.approvals_file = self.state_dir / "approvals.json"

    def classify(self, action_type: str, payload: Optional[Dict] = None) -> PolicyDecision:
        payload = payload or {}
        command = str(payload.get("command", "")).lower()
        profile = payload.get("project_profile") or {}
        allowed_without_approval = set(profile.get("allowed_without_approval", []))
        sensitive_actions = set(profile.get("sensitive_actions", []))

        if action_type in allowed_without_approval:
            return PolicyDecision("allow", f"Allowed by project profile: {profile.get('name', 'unknown')}.")

        if action_type in sensitive_actions:
            return PolicyDecision("approval", f"Sensitive action for project profile: {profile.get('name', 'unknown')}.")

        if action_type in {"read", "list", "status", "analysis", "draft"}:
            return PolicyDecision("allow", "Low-risk observation or draft action.")

        if action_type in {"publish", "deploy", "spend", "external_message"}:
            return PolicyDecision("approval", "External, economic, or brand-impacting action.")

        if action_type in {"install", "autonomous_start"}:
            return PolicyDecision("approval", "Changes runtime state or starts unattended work.")

        if action_type == "shell":
            destructive_markers = [
                "rm ",
                "del ",
                "rmdir",
                "format",
                "git reset --hard",
                "git checkout --",
                "drop database",
                "npm audit fix --force",
            ]
            if any(marker in command for marker in destructive_markers):
                return PolicyDecision("block", "Potentially destructive shell command.")
            return PolicyDecision("approval", "Arbitrary shell command requires approval.")

        return PolicyDecision("approval", "Unknown action type requires approval.")

    def log_action(self, action_type: str, payload: Dict, decision: PolicyDecision, status: str) -> Dict:
        record = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "payload": payload,
            "decision": {"level": decision.level, "reason": decision.reason},
            "status": status,
        }
        with open(self.actions_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def request_approval(self, action_type: str, payload: Dict, decision: PolicyDecision) -> Dict:
        record = self.log_action(action_type, payload, decision, "pending_approval")
        approvals = self._load_approvals()
        approvals[record["id"]] = record
        self._save_approvals(approvals)
        return record

    def resolve_approval(self, approval_id: str, approved: bool) -> Optional[Dict]:
        approvals = self._load_approvals()
        record = approvals.pop(approval_id, None)
        if not record:
            return None
        record["status"] = "approved" if approved else "rejected"
        record["resolved_at"] = datetime.now().isoformat()
        self._save_approvals(approvals)
        decision = PolicyDecision(record["decision"]["level"], record["decision"]["reason"])
        self.log_action(record["action_type"], record["payload"], decision, record["status"])
        return record

    def list_pending(self) -> Dict:
        return self._load_approvals()

    def _load_approvals(self) -> Dict:
        if not self.approvals_file.exists():
            return {}
        try:
            with open(self.approvals_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_approvals(self, approvals: Dict):
        with open(self.approvals_file, "w", encoding="utf-8") as f:
            json.dump(approvals, f, ensure_ascii=False, indent=2)
