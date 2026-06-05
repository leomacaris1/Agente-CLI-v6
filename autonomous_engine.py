import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


def _console(message: str):
    safe_message = message.encode("cp1252", errors="replace").decode("cp1252")
    print(safe_message)


class AutonomousEngine:
    def __init__(self, agent):
        self.agent = agent
        self.project_dir = Path.home() / "Desktop" / "Digital-Business"
        self.running = False
        self.current_task = None
        self.task_queue = []
        self.last_action = None
        self.decision_count = 0
        _console("[ENGINE] Inicializando motor autonomo...")
        self._load_state()

    def _load_state(self):
        state_file = self.project_dir / "autonomous_state.json"
        _console(f"[ENGINE] Buscando estado en: {state_file}")

        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.task_queue = state.get("queue", [])
                self.last_action = state.get("last_action")
                self.decision_count = state.get("decision_count", 0)
                _console(f"[ENGINE] Estado cargado. {len(self.task_queue)} tareas en cola.")
            except Exception as e:
                _console(f"[ENGINE] Error cargando estado: {e}. Reinicializando...")
                self._initialize_default_plan()
        else:
            _console("[ENGINE] No existe estado. Creando plan por defecto...")
            self._initialize_default_plan()

    def _initialize_default_plan(self):
        _console("[ENGINE] Inicializando plan de 30 dias...")
        self.task_queue = [
            {"task": "/define-niche", "priority": 1, "week": 1, "status": "pending"},
            {"task": "/create-mvp 'plantilla' 'nichos validados'", "priority": 2, "week": 1, "status": "pending"},
            {
                "task": "Generar contenido completo del producto: 'Planificador de Productividad Para Emprendedores'",
                "priority": 3,
                "week": 1,
                "status": "pending",
            },
            {"task": "/gumroad-publish", "priority": 1, "week": 1, "status": "pending"},
            {"task": "/generate-content 5 tiktok", "priority": 1, "week": 2, "status": "pending"},
            {"task": "/generate-content 5 instagram", "priority": 2, "week": 2, "status": "pending"},
            {"task": "/gumroad-sales", "priority": 1, "week": 3, "status": "pending"},
            {"task": "Analizar metricas y optimizar", "priority": 1, "week": 4, "status": "pending"},
        ]
        self._save_state()
        _console("[ENGINE] Plan inicializado y guardado.")

    def _save_state(self):
        self.project_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.project_dir / "autonomous_state.json"
        try:
            state = {
                "queue": self.task_queue,
                "last_action": self.last_action,
                "decision_count": self.decision_count,
                "updated": datetime.now().isoformat(),
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            _console(f"[ENGINE] Error guardando estado: {e}")

    def decide_next_action(self) -> Optional[Dict]:
        pending = [task for task in self.task_queue if task["status"] == "pending"]
        if not pending:
            _console("[ENGINE] Todas las tareas completadas.")
            return None
        pending.sort(key=lambda task: (task.get("priority", 99), task.get("week", 99)))
        next_task = pending[0]
        self.current_task = next_task
        self.decision_count += 1
        return next_task

    def execute_task(self, task: Dict) -> str:
        task_cmd = task["task"]
        _console(f"[AUTONOMO] Ejecutando: {task_cmd}")

        try:
            if task_cmd.startswith("/"):
                result = self.agent.talk(task_cmd)
            else:
                result = self._execute_custom_task(task_cmd)

            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            task["result"] = result[:500] if len(result) > 500 else result

            self.last_action = {
                "task": task_cmd,
                "result": result[:200],
                "timestamp": datetime.now().isoformat(),
            }

            self._save_state()
            self._send_notification(f"Tarea completada: {task_cmd[:50]}")
            return result
        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            self._send_notification(f"Tarea fallo: {task_cmd[:50]} - {e}")
            return f"Error: {e}"

    def _execute_custom_task(self, task: str) -> str:
        if "Generar contenido completo" in task:
            product_name = task.replace("Generar contenido completo del producto: '", "").replace("'", "")
            return self.agent.generate_product_content(product_name)
        if "investigar" in task.lower():
            return self.agent.talk(f"/delegate researcher {task}")
        if "analizar" in task.lower() or "metricas" in task.lower():
            return self.agent.track_metrics()
        return self.agent.talk(f"Realiza esta tarea: {task}")

    def _send_notification(self, message: str):
        result = self.agent._send_telegram(f"[AUTONOMO] {message}")
        if "Error" in result or "❌" in result:
            _console(f"[TELEGRAM] {result}")

    def run_cycle(self):
        _console("[AUTONOMO] Iniciando ciclo de decision...")
        next_task = self.decide_next_action()

        if not next_task:
            self._send_notification("Todas las tareas completadas.")
            return

        self.execute_task(next_task)
        _console("[AUTONOMO] Ciclo completado")

    def start_autonomous_mode(self, interval_minutes=30):
        _console(f"[AUTONOMO] Iniciando modo autonomo (cada {interval_minutes} min)")
        self._send_notification(f"Modo autonomo ACTIVADO. Intervalo: {interval_minutes} min")
        self.running = True

        def autonomous_loop():
            while self.running:
                try:
                    self.run_cycle()
                    time.sleep(interval_minutes * 60)
                except Exception as e:
                    _console(f"[AUTONOMO] Error critico: {e}")
                    time.sleep(60)

        thread = threading.Thread(target=autonomous_loop, daemon=True)
        thread.start()
        return (
            "Modo autonomo INICIADO\n"
            f"Intervalo: {interval_minutes} minutos\n"
            f"Tareas en cola: {len(self.task_queue)}"
        )

    def stop_autonomous_mode(self):
        self.running = False
        self._send_notification("Modo autonomo PAUSADO")
        return "Modo autonomo DETENIDO"

    def get_status(self) -> str:
        pending = len([task for task in self.task_queue if task["status"] == "pending"])
        completed = len([task for task in self.task_queue if task["status"] == "completed"])
        failed = len([task for task in self.task_queue if task["status"] == "failed"])

        status = (
            "# Estado del Agente Autonomo\n"
            "## Configuracion\n"
            f"- Estado: {'ACTIVO' if self.running else 'INACTIVO'}\n"
            f"- Decisiones tomadas: {self.decision_count}\n"
            f"- Ultima accion: {self.last_action['task'] if self.last_action else 'Ninguna'}\n\n"
            "## Progreso del Proyecto\n"
            f"- Completadas: {completed}\n"
            f"- Pendientes: {pending}\n"
            f"- Fallidas: {failed}\n"
            f"- Total: {len(self.task_queue)}\n\n"
            "## Proximas Tareas\n"
        )
        pending_tasks = [task for task in self.task_queue if task["status"] == "pending"][:5]
        for index, task in enumerate(pending_tasks, 1):
            status += f"{index}. {task['task'][:60]}...\n"
        return status
