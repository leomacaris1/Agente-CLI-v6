import json
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class WorkQueue:
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.queue_file = self.state_dir / "work_queue.json"

    def add_task(
        self,
        title: str,
        project: str,
        action_type: str,
        worker: str,
        requires_approval: bool,
        priority: str = "normal",
        status: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        with self._locked():
            tasks = self._load()
            task = {
                "id": str(uuid.uuid4())[:8],
                "title": title,
                "project": project,
                "action_type": action_type,
                "worker": worker,
                "priority": priority,
                "requires_approval": requires_approval,
                "status": status or ("needs_approval" if requires_approval else "queued"),
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            tasks.append(task)
            self._save(tasks)
            return task

    def list_tasks(self, status: Optional[str] = None, project: Optional[str] = None) -> List[Dict]:
        tasks = self._load()
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        if project:
            tasks = [task for task in tasks if task.get("project") == project]
        return tasks

    def get_task(self, task_id: str) -> Optional[Dict]:
        return next((task for task in self._load() if task.get("id") == task_id), None)

    def update_status(self, task_id: str, status: str, note: str = "") -> Optional[Dict]:
        with self._locked():
            tasks = self._load()
            for task in tasks:
                if task.get("id") == task_id:
                    task["status"] = status
                    task["updated_at"] = datetime.now().isoformat()
                    if note:
                        task.setdefault("notes", []).append({"at": datetime.now().isoformat(), "note": note})
                    self._save(tasks)
                    return task
        return None

    def update_task(self, task_id: str, updates: Dict, note: str = "") -> Optional[Dict]:
        with self._locked():
            tasks = self._load()
            for task in tasks:
                if task.get("id") == task_id:
                    task.update(updates)
                    task["updated_at"] = datetime.now().isoformat()
                    if note:
                        task.setdefault("notes", []).append({"at": datetime.now().isoformat(), "note": note})
                    self._save(tasks)
                    return task
        return None

    def next_task(self, project: Optional[str] = None) -> Optional[Dict]:
        priority_rank = {"high": 0, "normal": 1, "low": 2}
        queued = self.list_tasks(status="queued", project=project)
        queued.sort(key=lambda task: (priority_rank.get(task.get("priority", "normal"), 1), task.get("created_at", "")))
        return queued[0] if queued else None

    def _load(self) -> List[Dict]:
        if not self.queue_file.exists():
            return []
        try:
            with open(self.queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, tasks: List[Dict]):
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)

    @contextmanager
    def _locked(self):
        yield
