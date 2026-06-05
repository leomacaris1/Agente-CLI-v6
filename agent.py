# agent.py — Agent CLI v6 + Autónomo + Gumroad
import os
import subprocess
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from urllib.parse import quote

from openai import OpenAI
from dotenv import load_dotenv

from memory import MemoryBank
from subagents import SubAgentRegistry
from autonomous_engine import AutonomousEngine
from gumroad_api import GumroadAPI
from governance import Governance, PolicyDecision
from project_profiles import build_project_profiles
from task_router import TaskRouter
from work_queue import WorkQueue
from internal_skills import InternalSkillRegistry
from telegram_operator import TelegramOperator
from daemon_runner import DaemonRunner
from budget_policy import BudgetPolicy
from agent_business import (
    check_gumroad_sales as business_check_gumroad_sales,
    generate_content_batch as business_generate_content_batch,
    generate_product_content as business_generate_product_content,
    list_gumroad_products as business_list_gumroad_products,
    publish_to_gumroad as business_publish_to_gumroad,
    setup_store as business_setup_store,
    track_metrics as business_track_metrics,
)
from agent_command_router import handle_agent_command

load_dotenv()
CURRENT_DATE = datetime.now().strftime('%d de %B de %Y')
NATIVE_TOOLS = []

class Agent:
    def __init__(self):
        self.model = os.getenv("MODEL", "meta-llama/llama-3.1-70b-instruct")
        self.api_key = os.getenv("API_KEY")
        self.api_base = "https://openrouter.ai/api/v1"
        self.CURRENT_DATE = CURRENT_DATE
        
        if not self.api_key:
            print("⚠️ Error: No se encontró API_KEY en .env")
            self.client = None
        else:
            self.client = OpenAI(base_url=self.api_base, api_key=self.api_key)
            
        self.current_dir = Path.cwd()
        self.projects = {
            'agent': Path.cwd(),
            'mmnexus': Path(os.getenv("MMNEXUS_PATH", "C:/Users/leoma/mmnexus-hub")),
            'fabrica': Path(os.getenv("FABRICA_PATH", "C:/Users/leoma/OneDrive/Desktop/Apps/fabrica-productos-digitales"))
        }
        self.current_project = "agent"
        self.project_profiles = build_project_profiles(self.projects)
        self.task_router = TaskRouter(self.project_profiles)
        self.history = []
        self.memory = MemoryBank()
        self.governance = Governance()
        self.work_queue = WorkQueue(self.governance.state_dir)
        self.internal_skills = InternalSkillRegistry()
        self.telegram_operator = TelegramOperator()
        self.budget_policy = BudgetPolicy(self.governance.state_dir)
        self.daemon_runner = DaemonRunner(self, self.governance.state_dir)
        self._approved_once = set()
        self.subagents = SubAgentRegistry(self)
        self.autonomous_engine = AutonomousEngine(self)
        self.gumroad = GumroadAPI(os.getenv("GUMROAD_TOKEN", ""))
        self._load_history()

    def _guard_action(self, action_type, payload):
        payload = dict(payload)
        profile_name = payload.get("project", self.current_project)
        profile = self.project_profiles.get(profile_name, self.get_current_project_profile())
        payload["project"] = profile.name
        payload["project_profile"] = {
            "name": profile.name,
            "allowed_without_approval": profile.allowed_without_approval,
            "sensitive_actions": profile.sensitive_actions,
        }
        command = payload.get("command")
        if command and command in self._approved_once:
            self._approved_once.remove(command)
            decision = PolicyDecision("allow", "Approved by user.")
            self.governance.log_action(action_type, payload, decision, "executed")
            return None

        decision = self.governance.classify(action_type, payload)
        if decision.level == "allow":
            self.governance.log_action(action_type, payload, decision, "executed")
            return None
        if decision.level == "block":
            self.governance.log_action(action_type, payload, decision, "blocked")
            return f"Accion bloqueada por politica: {decision.reason}"

        approval = self.governance.request_approval(action_type, payload, decision)
        msg = (
            "Aprobacion requerida\n"
            f"ID: {approval['id']}\n"
            f"Accion: {action_type}\n"
            f"Motivo: {decision.reason}\n"
            f"Comando: {payload.get('command', payload.get('summary', 'N/A'))}\n\n"
            f"Usa /approve {approval['id']} para ejecutar o /reject {approval['id']} para cancelar."
        )
        self._send_telegram(msg)
        return msg

    def telegram_status(self):
        return self.telegram_operator.format_digest(
            queue_summary=self.daily_brief(compact=True),
            approvals_summary=self.list_approvals(),
            projects_summary=self.list_projects(),
        )

    def telegram_send_status(self):
        status = self.telegram_status()
        return self.telegram_operator.send_message(status)

    def telegram_help(self):
        return self.telegram_operator.format_help()

    def telegram_diagnose(self):
        return self.telegram_operator.diagnose()

    def handle_telegram_command(self, text, chat_id=None):
        chat_id = str(chat_id or self.telegram_operator.chat_id)
        if not self.telegram_operator.is_authorized(chat_id):
            return "Chat no autorizado."

        command = text.strip()
        command_lower = command.lower()
        aliases = {
            "/start": "/tg-help",
            "/help": "/tg-help",
            "/tg": "/tg-help",
            "/status": "/tg-status",
            "ok": "/tg-status",
            "okay": "/tg-status",
            "dale": "/tg-status",
            "gracias": "/tg-status",
        }
        command = aliases.get(command_lower, command)

        if command_lower == "/approve":
            return "Uso: /approve <id>. Mira los IDs con /approvals."
        if command_lower == "/reject":
            return "Uso: /reject <id>. Mira los IDs con /approvals."
        if command_lower.startswith("/approve") and not command_lower.startswith("/approve "):
            return "Uso: /approve <id>."
        if command_lower.startswith("/reject") and not command_lower.startswith("/reject "):
            return "Uso: /reject <id>."

        allowed_prefixes = (
            "/tg-help",
            "/tg-status",
            "/tg-diagnose",
            "/daily-brief",
            "/budget",
            "/budget-check ",
            "/queue",
            "/queue-all",
            "/queue-next",
            "/approvals",
            "/approve ",
            "/reject ",
            "/propose-task ",
            "/route ",
            "/plan-task ",
            "/projects",
            "/multi-status",
            "/seed-multi-project",
            "/project-profile",
            "/policy",
            "/daemon-status",
        )
        if os.getenv("TELEGRAM_ALLOW_RUN", "true").lower() == "true":
            allowed_prefixes = allowed_prefixes + ("/queue-run-next",)
        if not command.startswith(allowed_prefixes):
            return "Comando no permitido por Telegram. Usa /tg-help."
        return self.talk(command)

    def daemon_status(self):
        return self.daemon_runner.status()

    def daemon_once(self, project=None):
        return self.daemon_runner.run_once(project=project)

    def daemon_send_digest(self):
        return self.telegram_operator.send_message(self.telegram_status())

    def secret_health_check(self):
        script = self.current_dir / "scripts" / "check_secret_exposure.py"
        if not script.exists():
            return "No encontre scripts/check_secret_exposure.py."
        try:
            result = subprocess.run(
                ["python", str(script)],
                cwd=self.current_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception as exc:
            return f"Fallo ejecutando secret check: {exc}"

        output = (result.stdout or result.stderr or "").strip()
        if result.returncode == 0:
            return output or "Secret exposure check passed."
        return output or f"Secret exposure check failed with code {result.returncode}."

    def list_approvals(self):
        approvals = self.governance.list_pending()
        if not approvals:
            return "No hay aprobaciones pendientes."
        lines = ["Aprobaciones pendientes:"]
        for approval_id, record in approvals.items():
            payload = record.get("payload", {})
            lines.append(
                f"- {approval_id}: {record.get('action_type')} | "
                f"{payload.get('command', payload.get('summary', 'sin detalle'))}"
            )
        return "\n".join(lines)

    def approve_action(self, approval_id):
        record = self.governance.resolve_approval(approval_id, approved=True)
        if not record:
            return f"No encontre aprobacion pendiente con id {approval_id}."
        queue_task_id = record.get("payload", {}).get("queue_task_id")
        if queue_task_id:
            self.work_queue.update_status(queue_task_id, "queued", f"Aprobada por approval {approval_id}")
        command = record.get("payload", {}).get("command")
        if not command:
            return f"Aprobacion {approval_id} marcada como aprobada."
        self._approved_once.add(command)
        return f"Aprobado {approval_id}. Ejecutando...\n\n{self.talk(command)}"

    def reject_action(self, approval_id):
        record = self.governance.resolve_approval(approval_id, approved=False)
        if not record:
            return f"No encontre aprobacion pendiente con id {approval_id}."
        queue_task_id = record.get("payload", {}).get("queue_task_id")
        if queue_task_id:
            self.work_queue.update_status(queue_task_id, "rejected", f"Rechazada por approval {approval_id}")
        return f"Aprobacion {approval_id} rechazada."

    def autonomy_policy(self):
        return (
            "Politica de autonomia:\n"
            "- Permitido: leer, listar, analizar, generar borradores y reportes.\n"
            "- Requiere aprobacion: shell, installs, publicar, deploy, modo autonomo.\n"
            "- Bloqueado: borrados destructivos, reset hard, gastos, cambios legales/credenciales.\n"
            "Ver AUTONOMY_POLICY.md para el detalle."
        )

    def daily_brief(self, compact=False):
        all_tasks = self.work_queue.list_tasks()
        pending = [task for task in all_tasks if task.get("status") in {"queued", "needs_approval", "running"}]
        queued = [task for task in all_tasks if task.get("status") == "queued"]
        approvals = self.governance.list_pending()

        by_project = {}
        for name in self.projects:
            by_project[name] = {
                "queued": len([task for task in queued if task.get("project") == name]),
                "pending": len([task for task in pending if task.get("project") == name]),
                "path_ok": self.projects[name].exists(),
            }

        next_task = self.work_queue.next_task()
        lines = [
            "Daily brief multi-proyecto",
            f"- Fecha: {datetime.now().isoformat(timespec='minutes')}",
            f"- Tareas pendientes: {len(pending)}",
            f"- Aprobaciones pendientes: {len(approvals)}",
        ]

        if next_task:
            lines.append(
                f"- Proxima tarea segura: {next_task['id']} "
                f"{next_task['project']}/{next_task['worker']} - {next_task['title']}"
            )
        else:
            lines.append("- Proxima tarea segura: ninguna")

        lines.append("")
        lines.append("Proyectos")
        for name, info in by_project.items():
            lines.append(
                f"- {name}: ruta={'ok' if info['path_ok'] else 'no existe'}, "
                f"queued={info['queued']}, pending={info['pending']}"
            )

        lines.append("")
        lines.append("Autonomia")
        lines.append("- Puede ejecutar: lectura, analisis, borradores y generacion de contenido.")
        lines.append("- Debe pedir aprobacion: deploy, publicacion, gasto, mensajes externos, installs y shell.")
        lines.append("- Bloqueado: borrado destructivo, reset hard, credenciales y acciones irreversibles sin orden explicita.")

        if not compact:
            lines.append("")
            lines.append("Economia")
            lines.append(f"- Archivo de politica: {self.budget_policy.policy_file}")
            lines.extend(self.budget_policy.summary().splitlines()[1:])

            lines.append("")
            lines.append("Siguientes pasos")
            lines.append("- MMNexus: probar POST /api/telemetry tras deploy y confirmar Firestore.")
            lines.append("- Fabrica: extender perfiles por tipo de salida y empaquetado comercial.")
            lines.append("- Agente: correr daemon local supervisado y enviar digest por Telegram.")

        return "\n".join(lines)

    def send_daily_brief(self):
        return self.telegram_operator.send_message(self.daily_brief())

    def budget_summary(self):
        return self.budget_policy.summary()

    def budget_check(self, raw):
        parts = raw.split(" ", 2)
        if len(parts) < 2:
            return "Uso: /budget-check <monto> <categoria> [descripcion]"
        try:
            amount = float(parts[0].replace(",", "."))
        except ValueError:
            return "Monto invalido."
        category = parts[1]
        description = parts[2] if len(parts) == 3 else ""
        result = self.budget_policy.evaluate(amount, category, description)
        return f"Decision economica: {result['decision']}\nMotivo: {result['reason']}"

    def get_current_project_profile(self):
        return self.project_profiles.get(self.current_project, self.project_profiles["agent"])

    def list_projects(self):
        lines = ["Proyectos configurados:"]
        for name, path in self.projects.items():
            marker = "*" if name == self.current_project else "-"
            exists = "ok" if path.exists() else "no existe"
            lines.append(f"{marker} {name}: {path} ({exists})")
        return "\n".join(lines)

    def multi_project_status(self):
        lines = ["Estado multi-proyecto:"]
        for name, path in self.projects.items():
            exists = path.exists()
            package_json = path / "package.json"
            app_package_json = path / "apps" / "web" / "package.json"
            git_dir = path / ".git"
            profile = self.project_profiles.get(name)
            queued = len(self.work_queue.list_tasks(project=name))
            lines.append(
                f"- {name}: {'ok' if exists else 'no existe'} | "
                f"git={'si' if git_dir.exists() else 'no'} | "
                f"package={'si' if package_json.exists() or app_package_json.exists() else 'no'} | "
                f"tareas={queued} | "
                f"mision={profile.mission if profile else 'sin perfil'}"
            )
        return "\n".join(lines)

    def seed_multi_project_queue(self):
        seeds = [
            {
                "title": "MMNexus: ejecutar probe de telemetria y documentar si Firestore guarda eventos",
                "project": "mmnexus",
                "action_type": "analysis",
                "worker": "auditor",
                "priority": "high",
                "requires_approval": False,
                "metadata": {
                    "origin": "multi_project_seed",
                    "acceptance": "Confirmar GET/POST /api/telemetry, Firestore y Analytics con datos visibles."
                },
            },
            {
                "title": "Fabrica: ampliar perfiles de salida para ebook, curso, video, app y redes",
                "project": "fabrica",
                "action_type": "content_generation",
                "worker": "creator",
                "priority": "high",
                "requires_approval": False,
                "metadata": {
                    "origin": "multi_project_seed",
                    "acceptance": "Cada propuesta debe producir maqueta, portada/thumbnail, copy y checklist."
                },
            },
            {
                "title": "Agente: conectar reportes multi-proyecto con Telegram y aprobaciones sensibles",
                "project": "agent",
                "action_type": "draft",
                "worker": "planner",
                "priority": "high",
                "requires_approval": False,
                "metadata": {
                    "origin": "multi_project_seed",
                    "acceptance": "Telegram debe mostrar estado, cola, approvals y proximo paso por proyecto."
                },
            },
            {
                "title": "MMNexus: preparar checklist para Pinterest sin publicar ni usar credenciales",
                "project": "mmnexus",
                "action_type": "draft",
                "worker": "planner",
                "priority": "normal",
                "requires_approval": False,
                "metadata": {
                    "origin": "multi_project_seed",
                    "acceptance": "Checklist separa prerequisites, pruebas locales, aprobacion y publicacion."
                },
            },
            {
                "title": "Agente: definir alternativa a Oracle Cloud para runtime 24/7",
                "project": "agent",
                "action_type": "analysis",
                "worker": "auditor",
                "priority": "normal",
                "requires_approval": False,
                "metadata": {
                    "origin": "multi_project_seed",
                    "acceptance": "Comparar local always-on, VPS barato, Render/Fly y Oracle cuando se desbloquee."
                },
            },
        ]
        created = []
        existing_titles = {task.get("title") for task in self.work_queue.list_tasks()}
        for seed in seeds:
            if seed["title"] in existing_titles:
                continue
            task = self.work_queue.add_task(**seed)
            created.append(task)

        if not created:
            return "La cola multi-proyecto ya tenia estas tareas base."

        lines = ["Tareas multi-proyecto creadas:"]
        for task in created:
            lines.append(f"- {task['id']} [{task['project']}/{task['worker']}]: {task['title']}")
        return "\n".join(lines)

    def project_profile_summary(self, name=None):
        profile = self.project_profiles.get(name or self.current_project)
        if not profile:
            return f"No encontre perfil para '{name}'."
        notes = "\n".join([f"- {note}" for note in profile.autonomy_notes])
        sensitive = ", ".join(profile.sensitive_actions) or "ninguna"
        allowed = ", ".join(profile.allowed_without_approval) or "ninguna"
        return (
            f"Perfil: {profile.name}\n"
            f"Ruta: {profile.path}\n"
            f"Mision: {profile.mission}\n"
            f"Permitido sin aprobacion: {allowed}\n"
            f"Sensible: {sensitive}\n"
            f"Notas:\n{notes}"
        )

    def route_task(self, task):
        route = self.task_router.route(task, self.current_project)
        approval = "si" if route.requires_approval else "no"
        return (
            "Ruta sugerida:\n"
            f"- Proyecto: {route.project}\n"
            f"- Accion: {route.action_type}\n"
            f"- Worker: {route.worker}\n"
            f"- Requiere aprobacion: {approval}\n"
            f"- Confianza: {route.confidence}\n"
            f"- Motivo: {route.reason}"
        )

    def plan_routed_task(self, task):
        route = self.task_router.route(task, self.current_project)
        profile = self.project_profiles.get(route.project)
        decision = self.governance.classify(
            route.action_type,
            {
                "command": task,
                "project": route.project,
                "project_profile": {
                    "name": profile.name,
                    "allowed_without_approval": profile.allowed_without_approval,
                    "sensitive_actions": profile.sensitive_actions,
                } if profile else {},
            },
        )
        return (
            f"{self.route_task(task)}\n"
            f"- Decision politica: {decision.level}\n"
            f"- Razon politica: {decision.reason}\n\n"
            "Siguiente paso recomendado: preparar ejecucion en modo borrador o pedir aprobacion si toca una accion sensible."
        )

    def propose_task(self, task):
        route = self.task_router.route(task, self.current_project)
        queue_task = self.work_queue.add_task(
            title=task,
            project=route.project,
            action_type=route.action_type,
            worker=route.worker,
            requires_approval=route.requires_approval,
            metadata={
                "confidence": route.confidence,
                "reason": route.reason,
            },
        )
        payload = {
            "command": f"/plan-task {task}",
            "summary": task,
            "project": route.project,
            "action_type": route.action_type,
            "worker": route.worker,
            "confidence": route.confidence,
            "queue_task_id": queue_task["id"],
        }
        if route.requires_approval:
            blocked = self._guard_action(route.action_type, payload)
            if blocked:
                return f"{self.route_task(task)}\n\nTarea en cola: {queue_task['id']} ({queue_task['status']})\n\n{blocked}"
        decision = PolicyDecision("allow", "Routed task proposal recorded.")
        self.governance.log_action(route.action_type, payload, decision, "proposed")
        return f"{self.route_task(task)}\n\nTarea en cola: {queue_task['id']} ({queue_task['status']})"

    def list_queue(self, status=None, include_done=False):
        tasks = self.work_queue.list_tasks(status=status)
        if status is None and not include_done:
            active_statuses = {"queued", "needs_approval", "running", "failed"}
            tasks = [task for task in tasks if task.get("status") in active_statuses]
        if not tasks:
            return "No hay tareas activas. Usa /queue-all para ver historial."
        lines = ["Cola de trabajo:"]
        for task in tasks[-20:]:
            approval = "approval" if task.get("requires_approval") else "auto"
            lines.append(
                f"- {task['id']} [{task['status']}] {task['project']}/{task['worker']} "
                f"({task['priority']}, {approval}): {task['title']}"
            )
        return "\n".join(lines)

    def queue_next(self, project=None):
        task = self.work_queue.next_task(project=project)
        if not task:
            return "No hay tareas en estado queued."
        return (
            "Proxima tarea:\n"
            f"- ID: {task['id']}\n"
            f"- Proyecto: {task['project']}\n"
            f"- Worker: {task['worker']}\n"
            f"- Accion: {task['action_type']}\n"
            f"- Titulo: {task['title']}"
        )

    def queue_update(self, task_id, status, note=""):
        task = self.work_queue.update_status(task_id, status, note)
        if not task:
            return f"No encontre tarea con id {task_id}."
        return f"Tarea {task_id} actualizada a {status}."

    def queue_run_next(self, project=None):
        task = self.work_queue.next_task(project=project)
        if not task:
            return "No hay tareas queued para ejecutar."
        return self.queue_run_task(task["id"])

    def queue_run_task(self, task_id):
        task = self.work_queue.get_task(task_id)
        if not task:
            return f"No encontre tarea con id {task_id}."
        if task.get("status") != "queued":
            return f"La tarea {task_id} esta en estado {task.get('status')}, no queued."

        decision = self._queue_execution_decision(task)
        if decision:
            return decision

        self.work_queue.update_status(task_id, "running", "Ejecucion iniciada por queue runner.")
        try:
            result = self._execute_queue_task(task)
            self.work_queue.update_task(
                task_id,
                {"status": "done", "result": result[:1000]},
                "Ejecucion completada.",
            )
            return f"Tarea {task_id} completada.\n\n{result}"
        except Exception as e:
            self.work_queue.update_task(
                task_id,
                {"status": "failed", "error": str(e)},
                "Ejecucion fallo.",
            )
            return f"Tarea {task_id} fallo: {e}"

    def _queue_execution_decision(self, task):
        action_type = task.get("action_type")
        if task.get("requires_approval"):
            return f"La tarea {task['id']} requiere aprobacion antes de ejecutarse."
        allowed_actions = {"read", "analysis", "draft", "content_generation"}
        if action_type not in allowed_actions:
            return f"La accion {action_type} todavia no tiene executor seguro."
        return None

    def _execute_queue_task(self, task):
        action_type = task.get("action_type")
        title = task.get("title", "")
        project = task.get("project", self.current_project)
        project_path = self.projects.get(project, self.current_dir)
        output_root = self._project_artifacts_dir(project)

        return self.internal_skills.run(
            action_type=action_type,
            worker=task.get("worker", "generalist"),
            title=title,
            project=project,
            project_path=project_path,
            output_root=output_root,
        )

    def _project_artifacts_dir(self, project):
        write_to_project = os.getenv("AGENT_WRITE_PROJECT_OUTPUTS", "false").lower() == "true"
        base = self.projects.get(project, self.current_dir) if write_to_project else self.governance.state_dir / "outputs" / project
        target = base / ".agent_outputs" if write_to_project else base
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _safe_task_filename(self, task_id_or_title):
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in task_id_or_title)
        return "_".join(part for part in safe.split("_") if part)[:80] or "task"

    def _write_queue_artifact(self, project, title, content):
        artifacts_dir = self._project_artifacts_dir(project)
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._safe_task_filename(title)}.md"
        path = artifacts_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _execute_read_task(self, title, project):
        profile = self.project_profiles.get(project)
        target = profile.path if profile else self.current_dir
        summary = f"# Resultado de lectura\n\nTarea: {title}\nProyecto: {project}\nRuta: {target}\n\n{self._list_dir('.') if target == self.current_dir else 'Directorio preparado para inspeccion.'}\n"
        path = self._write_queue_artifact(project, title, summary)
        return f"Artefacto generado: {path}"

    def _execute_analysis_task(self, title, project):
        content = (
            f"# Analisis\n\n"
            f"Proyecto: {project}\n"
            f"Tarea: {title}\n\n"
            "## Observaciones iniciales\n"
            "- Tarea clasificada para analisis seguro.\n"
            "- No se realizaron cambios de codigo ni acciones externas.\n\n"
            "## Proximo paso\n"
            "- Convertir este analisis en checklist ejecutable o pedir aprobacion si requiere accion sensible.\n"
        )
        path = self._write_queue_artifact(project, title, content)
        return f"Analisis generado: {path}"

    def _execute_draft_task(self, title, project):
        content = (
            f"# Borrador operativo\n\n"
            f"Proyecto: {project}\n"
            f"Tarea: {title}\n\n"
            "## Propuesta\n"
            "- Objetivo: definir una salida trabajable sin ejecutar cambios sensibles.\n"
            "- Entregable: especificacion, pasos y criterios de aceptacion.\n\n"
            "## Checklist\n"
            "- [ ] Confirmar alcance.\n"
            "- [ ] Crear artefactos necesarios.\n"
            "- [ ] Revisar calidad.\n"
            "- [ ] Pedir aprobacion si hay publicacion, deploy, gasto o comando externo.\n"
        )
        path = self._write_queue_artifact(project, title, content)
        return f"Borrador generado: {path}"

    def _execute_content_generation_task(self, title, project):
        content = (
            f"# Paquete de contenido\n\n"
            f"Proyecto: {project}\n"
            f"Tarea: {title}\n\n"
            "## Entregables sugeridos\n"
            "- Pieza principal de contenido.\n"
            "- Brief visual o maqueta.\n"
            "- Copy de publicacion.\n"
            "- Checklist de revision.\n\n"
            "## Borrador inicial\n"
            "Este artefacto reserva el trabajo de generacion para una skill especializada. "
            "Puede enriquecerse con un creador de productos digitales, generador de portada o launch kit.\n"
        )
        path = self._write_queue_artifact(project, title, content)
        return f"Contenido base generado: {path}"

    def _load_history(self):
        try:
            hf = Path.home() / ".agent_cli_history.json"
            if hf.exists():
                with open(hf, 'r', encoding='utf-8') as f:
                    self.history = json.load(f).get('history', [])
        except: 
            self.history = []

    def _save_history(self):
        try:
            with open(Path.home() / ".agent_cli_history.json", 'w', encoding='utf-8') as f:
                json.dump({'history': self.history[-15:]}, f, ensure_ascii=False, indent=2)
        except: 
            pass

    def _list_dir(self, path="."):
        target = self.current_dir / path
        if not target.exists(): return "❌ Ruta no existe"
        items = [f"{'📁 ' if i.is_dir() else '📄 '} {i.name}" for i in target.iterdir() if not i.name.startswith('.')]
        return "\n".join(items) if items else "📂 Vacío"

    def _read_file(self, path):
        try:
            target = self.current_dir / Path(path.replace('\\', '/'))
            if not target.exists(): return f"❌ No existe: {path}"
            with open(target, 'r', encoding='utf-8') as f: c = f.read()
            return c if len(c) < 8000 else c[:7500] + "\n... (truncado)"
        except Exception as e: return f"❌ Error: {e}"

    def _run_command(self, cmd, timeout=60):
        print(f"🔧 Ejecutando: {cmd}")
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.current_dir, timeout=timeout)
            out = r.stdout if r.stdout else r.stderr
            return out.strip() if out.strip() else "✅ Ejecutado"
        except subprocess.TimeoutExpired: return "⏱️ Timeout"
        except Exception as e: return f"❌ Error: {e}"

    def _write_file(self, path, content):
        target = self.current_dir / path
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, 'w', encoding='utf-8') as f: f.write(content)
            return f"✅ Guardado: {path}"
        except Exception as e: return f"❌ Error: {e}"

    def _send_telegram(self, msg):
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            if not token or not chat_id: 
                print("⚠️ [TELEGRAM] No configurado en .env")
                return "⚠️ Telegram no configurado"
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg[:3900]}, timeout=10)
            if r.status_code == 200:
                return "✅ Enviado"
            else:
                print(f"⚠️ [TELEGRAM] Error {r.status_code}: {r.text}")
                return f"❌ Error Telegram: {r.text}"
        except Exception as e: 
            print(f"❌ [TELEGRAM] Excepción: {e}")
            return f"❌ Error Telegram: {e}"

    def scrape_docs(self, topic):
        print(f"📚 Docs: {topic}")
        urls = [f"https://nextjs.org/docs/{quote(topic)}", f"https://react.dev/reference/{quote(topic)}"]
        results = []
        for u in urls:
            try:
                r = requests.get(f"https://r.jina.ai/{u}", timeout=10)
                if r.status_code == 200: results.append(f"📄 {u}\n{r.text[:1500]}")
            except: continue
        if results:
            content = "\n\n---\n\n".join(results)
            doc_file = self.current_dir / f"docs_{topic.replace(' ', '_')}.md"
            with open(doc_file, 'w', encoding='utf-8') as f: f.write(content)
            self._send_telegram(f"📚 Docs guardadas:\n📄 {doc_file.name}")
            return content
        return f"❌ No se encontró docs para '{topic}'"

    def audit_project(self, task=None):
        print("🚀 Auditoría...")
        self._send_telegram(f"🔍 Auditoría en: {self.current_dir.name}")
        report = ["# 🔍 AUDITORÍA TÉCNICA", f"**Fecha:** {CURRENT_DATE}", f"**Directorio:** {self.current_dir}", "", "## 📁 Estructura", f"```\n{self._list_dir('.')}\n```", "", "## 📦 Package.json"]
        pkg = self.current_dir / "package.json"
        if pkg.exists():
            try:
                with open(pkg, 'r', encoding='utf-8') as f: p = json.load(f)
                report += [f"- **Nombre:** {p.get('name','N/A')}", f"- **Versión:** {p.get('version','N/A')}", f"- **Dependencias:** {len(p.get('dependencies',{}))}"]
            except Exception as e: report.append(f"❌ Error: {e}")
        else: report.append("❌ No encontrado")
        report += ["", "## 🚨 Vulnerabilidades"]
        if (self.current_dir / "node_modules").exists():
            res = self._run_command("npm audit --json", timeout=120)
            try:
                data = json.loads(res)
                vulns = data.get("vulnerabilities", {})
                if not vulns: report.append("✅ Sin vulnerabilidades")
                else:
                    counts = {}
                    for v in vulns.values():
                        sev = v.get("severity", "low").lower()
                        counts[sev] = counts.get(sev, 0) + 1
                    for l, c in counts.items(): report.append(f"- {l.upper()}: {c}")
            except: report.append("⚠️ Error en npm audit")
        else: report.append("⚠️ Sin node_modules")
        report += ["\n---\n*Agent CLI v6*"]
        content = "\n".join(report)
        report_file = self.current_dir / "AUDIT_REPORT.md"
        try:
            with open(report_file, 'w', encoding='utf-8') as f: f.write(content)
            self._send_telegram("✅ Auditoría completada\n📄 AUDIT_REPORT.md")
            return f"✅ Auditoría completada\n\n📄 {report_file}\n\n{content}"
        except Exception as e: return f"❌ Error guardando reporte: {e}"

    def generate_code_task(self, task: str, filepath: Optional[str] = None):
        print(f"✨ Generando: {task}")
        prompt = f"Generá código TypeScript/React para: {task}. Requisitos: TypeScript, funcional, Tailwind si aplica, limpio. Solo código."
        try:
            res = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=2000)
            code = res.choices[0].message.content.replace("```typescript","").replace("```tsx","").replace("```","").strip()
            if filepath:
                target = self.current_dir / filepath
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, 'w', encoding='utf-8') as f: f.write(code)
                self._send_telegram(f"✨ Código guardado: {filepath}")
                return f"✅ Archivo: {filepath}\n\n```tsx\n{code[:600]}...\n```"
            return f"📋 Código:\n\n```tsx\n{code}\n```"
        except Exception as e: return f"❌ Error: {e}"

    def install_dependencies(self, task=None):
        print("📦 Instalando...")
        self._send_telegram(f"📦 Instalando en: {self.current_dir.name}")
        res = self._run_command("npm install", timeout=300)
        msg = f"✅ Instalación finalizada\n{res[:300]}"
        self._send_telegram(msg)
        return msg

    def debug_code(self, task=None):
        print("🐛 Debugging...")
        log_files = ["error.log", "npm-debug.log"]
        context = ""
        for f in log_files:
            if (self.current_dir / f).exists():
                context += self._read_file(f)
        prompt = f"""Sos un experto en debugging.
Contexto: {self._list_dir()}
Error: {task}
Logs: {context[:1000]}
Analizá y dale solución."""
        try:
            res = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=1500)
            return f"🐛 **Debug:**\n\n{res.choices[0].message.content}"
        except Exception as e: return f"❌ Error: {e}"

    def document_project(self, task=None):
        print("📝 Documentando...")
        prompt = f"Generá documentación técnica para: {self.current_dir}. Archivos: {self._list_dir()}"
        try:
            res = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=2000)
            doc_content = res.choices[0].message.content
            doc_file = self.current_dir / "GENERATED_README.md"
            with open(doc_file, 'w', encoding='utf-8') as f: f.write(doc_content)
            self._send_telegram("📝 Documentación: GENERATED_README.md")
            return f"✅ Doc guardada en `GENERATED_README.md`"
        except Exception as e: return f"❌ Error: {e}"

    def deploy_project(self, task=None):
        print(f"🚀 Deploying: {self.current_dir.name}")
        instructions = "# 🚀 Deploy\n\n1. vercel login\n2. vercel --prod"
        f_path = self.current_dir / "deploy.md"
        with open(f_path, 'w', encoding='utf-8') as f: f.write(instructions)
        return "✅ Instrucciones en deploy.md"

    def switch_project(self, name):
        if name in self.projects:
            self.current_dir = self.projects[name]
            self.current_project = name
            if not self.current_dir.exists():
                return (
                    f"Proyecto configurado pero la ruta no existe: {self.current_dir}\n\n"
                    f"{self.project_profile_summary(name)}"
                )
            os.chdir(self.current_dir)
            self.history = []
            return f"📁 Proyecto: {name}\n📍 {self.current_dir}\n\n{self.project_profile_summary(name)}"
        return f"❌ Proyectos: {', '.join(self.projects.keys())}"

    def init_business_project(self):
        print("🚀 Inicializando negocio digital...")
        project_dir = Path.home() / "Desktop" / "Digital-Business"
        if not project_dir.exists():
            project_dir.mkdir(parents=True)
            for folder in ["assets", "content", "analytics", "social-media", "products", "reports"]:
                (project_dir / folder).mkdir(exist_ok=True)
        
        files = {
            "business_plan.md": f"# 📊 Plan de Negocio Digital\n\n**Estado:** En desarrollo\n**Presupuesto:** $0\n**Meta:** 30 días\n**Inicio:** {CURRENT_DATE}\n\n## 🎯 Nicho\n[Por definir]\n\n## 📦 Producto\n[Por definir]\n\n## 📈 Métricas\n- Visitas: 0\n- Leads: 0\n- Ventas: 0\n- Ingresos: $0\n",
            "daily_tasks.json": json.dumps({"tasks": [], "completed": [], "last_update": CURRENT_DATE}, indent=2, ensure_ascii=False),
            "dashboard.md": f"# 📊 Dashboard\n\n## Estado\n- **Día:** 1/30\n- **Presupuesto:** $0\n- **Ingresos:** $0\n- **Tareas:** 0\n\n## Progreso\n- [ ] Semana 1: Nicho\n- [ ] Semana 2: Producto\n- [ ] Semana 3: Marketing\n- [ ] Semana 4: Ventas\n\n*{CURRENT_DATE}*",
            "budget_tracker.json": json.dumps({"total_budget": 0, "spent": 0, "transactions": []}, indent=2)
        }
        
        for filename, content in files.items():
            with open(project_dir / filename, 'w', encoding='utf-8') as f:
                f.write(content)
        
        self._send_telegram("🚀 Negocio digital inicializado\n📁 Desktop/Digital-Business")
        return f"✅ Proyecto en `{project_dir}`\n\n📋 Archivos:\n- business_plan.md\n- dashboard.md\n- daily_tasks.json\n- budget_tracker.json"

    def define_niche(self, preferences=""):
        print("🔍 Analizando nichos...")
        prompt = f"""Analizá nichos rentables 2026, presupuesto $0.
Preferencias: {preferences}

Criterios:
- Demanda validada
- Márgenes >70%
- Digital (sin inventario)

Devolver JSON:
{{
  "recommended_niche": "nombre",
  "target_audience": "descripción",
  "pain_points": ["p1", "p2"],
  "product_ideas": ["idea1", "idea2"],
  "estimated_margin": "XX%"
}}"""
        try:
            res = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=1500)
            analysis = res.choices[0].message.content
            project_dir = Path.home() / "Desktop" / "Digital-Business"
            with open(project_dir / "niche_analysis.md", 'w', encoding='utf-8') as f:
                f.write(f"# 🔍 Análisis de Nicho\n\n{analysis}")
            self._send_telegram("🔍 Nicho analizado")
            return f"✅ Análisis:\n\n{analysis[:1000]}..."
        except Exception as e: return f"❌ Error: {e}"

    def create_mvp_product(self, product_type="plantilla", niche_info=""):
        print(f"✨ Creando MVP: {product_type}")
        prompt = f"""Producto MVP para: {niche_info}
Tipo: {product_type}

Requisitos:
- Digital (PDF/Notion/Canva)
- Soluciona problema específico
- Valor alto
- Entrega automática

Generar:
1. Título
2. Descripción (copywriting)
3. Estructura
4. Precio
5. Bonus"""
        try:
            res = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=2000)
            plan = res.choices[0].message.content
            project_dir = Path.home() / "Desktop" / "Digital-Business"
            with open(project_dir / "mvp_product_plan.md", 'w', encoding='utf-8') as f:
                f.write(f"# 📦 MVP\n\n{plan}")
            self._send_telegram("✨ MVP planificado")
            return f"✅ Plan:\n\n{plan[:1000]}..."
        except Exception as e: return f"❌ Error: {e}"

    def setup_store(self, platform="gumroad"):
        return business_setup_store(self, platform)
        print(f"🛒 Configurando {platform}...")
        guides = {
            "gumroad": "# 🛒 Gumroad (Gratis)\n\n1. gumroad.com → Start Selling\n2. Products → New Product\n3. Precio: $5-15\n4. Subir archivo digital\n5. Cover en Canva\n\nComisión: 10% + $0.30/venta",
            "instagram": "# 📱 Instagram Shop\n\n1. Cuenta Business\n2. Catálogo → Facebook\n3. Link en bio (Linktree)\n4. 3 Reels/semana\n5. Stories diarios",
            "tiktok": "# 🎵 TikTok Strategy\n\n1. Business Account\n2. Bio optimizada + link\n3. 3 videos/día (15-60s)\n4. Hooks 3s\n5. Trending sounds"
        }
        guide = guides.get(platform, "No disponible")
        project_dir = Path.home() / "Desktop" / "Digital-Business"
        with open(project_dir / f"{platform}_setup.md", 'w', encoding='utf-8') as f:
            f.write(guide)
        self._send_telegram(f"🛒 Guía: {platform}")
        return f"✅ Guía: `{platform}_setup.md`\n\n{guide}"

    def generate_content_batch(self, quantity=5, platform="tiktok"):
        return business_generate_content_batch(self, quantity, platform)
        print(f"📝 Generando {quantity} contenidos...")
        prompt = f"""{quantity} ideas contenido viral para {platform}.
Nicho: Productos digitales

Formato:
{{
  "hook": "apertura",
  "script": "guion",
  "visual": "descripción",
  "cta": "call to action",
  "hashtags": ["#tag1"]
}}"""
        try:
            res = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=3000)
            content = res.choices[0].message.content
            project_dir = Path.home() / "Desktop" / "Digital-Business"
            content_file = project_dir / "social-media" / f"content_{platform}.md"
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(f"# 📱 Content {platform}\n\n{content}")
            self._send_telegram(f"📝 {quantity} contenidos generados")
            return f"✅ Contenido:\n\n{content[:1000]}..."
        except Exception as e: return f"❌ Error: {e}"

    def track_metrics(self):
        return business_track_metrics(self)
        print("📊 Actualizando dashboard...")
        project_dir = Path.home() / "Desktop" / "Digital-Business"
        tasks_file = project_dir / "daily_tasks.json"
        completed = 0
        if tasks_file.exists():
            with open(tasks_file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    completed = len(data.get("completed", []))
                except: pass
        
        gumroad_stats = ""
        if self.gumroad.token:
            try:
                stats = self.gumroad.get_stats()
                if stats.get("success"):
                    gumroad_stats = f"\n\n## 💰 Ventas Gumroad\n- Productos activos: {stats['active_products']}\n- Ventas totales: {stats['total_sales']}\n- Ingresos: {stats['total_revenue']}"
            except:
                gumroad_stats = "\n\n## 💰 Ventas Gumroad\n⚠️ Error al conectar"
        
        dashboard = f"""# 📊 Dashboard

## Estado
- **Día:** 1/30
- **Presupuesto:** $0
- **Ingresos:** $0
- **Tareas completadas:** {completed}

## Semanas
- [ ] S1: Nicho
- [ ] S2: Producto
- [ ] S3: Marketing
- [ ] S4: Ventas
{gumroad_stats}

*{CURRENT_DATE}*"""
        
        with open(project_dir / "dashboard.md", 'w', encoding='utf-8') as f:
            f.write(dashboard)
        return f"📊 Dashboard actualizado\n\n{dashboard}"

    def add_task(self, task, priority="media"):
        project_dir = Path.home() / "Desktop" / "Digital-Business"
        tasks_file = project_dir / "daily_tasks.json"
        if not tasks_file.exists():
            return self.init_business_project()
        with open(tasks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data["tasks"].append({"task": task, "priority": priority, "created": CURRENT_DATE, "status": "pending"})
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return f"✅ Tarea: {task}\n📋 Prioridad: {priority}"

    def complete_task(self, task_index):
        project_dir = Path.home() / "Desktop" / "Digital-Business"
        tasks_file = project_dir / "daily_tasks.json"
        with open(tasks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if task_index < len(data["tasks"]):
            task = data["tasks"].pop(task_index)
            task["status"] = "completed"
            task["completed_date"] = CURRENT_DATE
            data["completed"].append(task)
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return f"✅ Completada: {task['task']}"
        return "❌ No encontrada"

    def list_tasks(self):
        project_dir = Path.home() / "Desktop" / "Digital-Business"
        tasks_file = project_dir / "daily_tasks.json"
        if not tasks_file.exists():
            return self.init_business_project()
        with open(tasks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        tasks = data.get("tasks", [])
        if not tasks:
            return "📋 Sin tareas"
        result = "📋 **Pendientes:**\n\n"
        for i, task in enumerate(tasks):
            emoji = "🔴" if task["priority"] == "alta" else "🟡" if task["priority"] == "media" else "🟢"
            result += f"{i}. {emoji} {task['task']} ({task['priority']})\n"
        result += f"\n✅ Completadas: {len(data.get('completed', []))}"
        return result

    def generate_product_content(self, product_name: str):
        return business_generate_product_content(self, product_name)
        print(f"📝 Generando contenido para: {product_name}")
        prompt = f"""Sos un experto creador de productos digitales.
Tu tarea es crear el contenido COMPLETO del siguiente producto:
NOMBRE: {product_name}

REQUISITOS:
1. El contenido debe ser extenso, útil y de alta calidad.
2. Estructura: Introducción, Pasos detallados, Ejemplos prácticos, Conclusión.
3. Formato: Markdown claro.
4. NO incluyas títulos de producto ni precios, solo el contenido que el usuario leerá.
"""
        try:
            res = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=4000)
            content = res.choices[0].message.content
            safe_name = product_name.replace(" ", "_").lower()
            file_path = Path.home() / "Desktop" / "Digital-Business" / "products" / f"{safe_name}.md"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {product_name}\n\n{content}")
            self._send_telegram(f"📄 Producto creado:\n📄 {file_path.name}")
            return f"✅ Contenido generado y guardado en `products/{safe_name}.md`. Listo para publicar."
        except Exception as e:
            return f"❌ Error generando contenido: {e}"

    def publish_to_gumroad(self, name="", description="", price_usd=5.0, content_file_path=""):
        return business_publish_to_gumroad(self, name, description, price_usd, content_file_path)
        if not self.gumroad.token:
            return "⚠️ Configurá GUMROAD_TOKEN en tu archivo .env"
        
        products_dir = Path.home() / "Desktop" / "Digital-Business" / "products"
        content_to_upload = ""
        
        if content_file_path:
            p_file = Path(content_file_path)
        else:
            if products_dir.exists():
                files = list(products_dir.glob("*.md"))
                if files:
                    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    p_file = files[0]
                else:
                    return "❌ No hay productos generados en la carpeta 'products'. Ejecutá 'Generar contenido...' primero."
            else:
                return "❌ No hay carpeta de productos."

        if p_file.exists():
            content_to_upload = p_file.read_text(encoding='utf-8')
            product_name = p_file.stem.replace("_", " ").title()
            
            prompt_desc = f"Crea una descripción de venta persuasiva y corta (max 100 palabras) para este producto:\n{content_to_upload[:1000]}"
            try:
                res = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt_desc}], max_tokens=300)
                description = res.choices[0].message.content
            except:
                description = f"Producto digital: {product_name}"
            
            print(f"🛒 Publicando en Gumroad: {product_name}")
            result = self.gumroad.create_product(product_name, description, price_usd, content_text=content_to_upload)
            
            if result.get("success"):
                self._send_telegram(f"🚀 ¡PUBLICADO!\n📦 {result['name']}\n💰 ${price_usd}\n🔗 {result['url']}")
                return f"✅ Producto publicado!\n\n📦 **{result['name']}**\n💰 Precio: {result['price']}\n🔗 Link: {result['url']}\n\n*El contenido ha sido subido automáticamente*"
            else:
                return f"❌ Error al publicar: {result.get('error', 'Error desconocido')}"
        else:
            return f"❌ Archivo no encontrado: {p_file}"

    def check_gumroad_sales(self):
        return business_check_gumroad_sales(self)
        if not self.gumroad.token:
            return "⚠️ Configurá GUMROAD_TOKEN en .env"
        
        print("💰 Verificando ventas en Gumroad...")
        stats = self.gumroad.get_stats()
        
        if not stats.get("success"):
            return f"❌ Error: {stats.get('error')}"
        
        report = f"""# 💰 Reporte de Ventas Gumroad

## Resumen
- **Productos activos:** {stats['active_products']}
- **Ventas totales:** {stats['total_sales']}
- **Ingresos totales:** {stats['total_revenue']}

## Últimas ventas
"""
        for sale in stats.get('recent_sales', []):
            report += f"- {sale.get('product_name', 'N/A')}: ${sale.get('price', 0)} ({sale.get('created_at', 'N/A')[:10]})\n"
        
        if not stats.get('recent_sales'):
            report += "_Sin ventas registradas aún_"
        
        self._send_telegram(f"💰 Ventas Gumroad:\nTotal: {stats['total_revenue']}\nVentas: {stats['total_sales']}")
        return report

    def list_gumroad_products(self):
        return business_list_gumroad_products(self)
        if not self.gumroad.token:
            return "⚠️ Configurá GUMROAD_TOKEN en .env"
        
        products = self.gumroad.list_products()
        if not products:
            return "📦 No hay productos en Gumroad"
        
        report = "# 📦 Productos en Gumroad\n\n"
        for p in products:
            status = "✅ Activo" if p.get("published") else "⏸️ Borrador"
            report += f"- **{p['name']}** ({status})\n  💰 ${p['price']/100:.2f} | 🔗 gumroad.com/l/{p.get('custom_permalink', p['id'])}\n\n"
        
        return report

    def talk(self, user_input):
        cmd = user_input.strip()
        handled = handle_agent_command(self, cmd)
        if handled is not None:
            return handled

        if cmd == '/approvals': return self.list_approvals()
        if cmd.startswith('/approve '): return self.approve_action(cmd.replace('/approve ', '').strip())
        if cmd.startswith('/reject '): return self.reject_action(cmd.replace('/reject ', '').strip())
        if cmd == '/policy': return self.autonomy_policy()
        if cmd == '/daily-brief': return self.daily_brief()
        if cmd == '/send-daily-brief': return self.send_daily_brief()
        if cmd == '/budget': return self.budget_summary()
        if cmd.startswith('/budget-check '): return self.budget_check(cmd.replace('/budget-check ', '').strip())
        if cmd == '/projects': return self.list_projects()
        if cmd == '/multi-status': return self.multi_project_status()
        if cmd == '/seed-multi-project': return self.seed_multi_project_queue()
        if cmd == '/project-profile': return self.project_profile_summary()
        if cmd.startswith('/project-profile '): return self.project_profile_summary(cmd.replace('/project-profile ', '').strip())
        if cmd == '/tg-help': return self.telegram_help()
        if cmd == '/tg-status': return self.telegram_status()
        if cmd == '/tg-diagnose': return self.telegram_diagnose()
        if cmd == '/tg-send-status': return self.telegram_send_status()
        if cmd == '/secret-check': return self.secret_health_check()
        if cmd.startswith('/tg-handle '): return self.handle_telegram_command(cmd.replace('/tg-handle ', '').strip())
        if cmd == '/daemon-status': return self.daemon_status()
        if cmd == '/daemon-once': return self.daemon_once()
        if cmd.startswith('/daemon-once '): return self.daemon_once(cmd.replace('/daemon-once ', '').strip())
        if cmd == '/daemon-send-digest': return self.daemon_send_digest()
        if cmd.startswith('/route '): return self.route_task(cmd.replace('/route ', '').strip())
        if cmd.startswith('/plan-task '): return self.plan_routed_task(cmd.replace('/plan-task ', '').strip())
        if cmd.startswith('/propose-task '): return self.propose_task(cmd.replace('/propose-task ', '').strip())
        if cmd == '/queue': return self.list_queue()
        if cmd == '/queue-all': return self.list_queue(include_done=True)
        if cmd.startswith('/queue '): return self.list_queue(cmd.replace('/queue ', '').strip())
        if cmd == '/queue-next': return self.queue_next()
        if cmd.startswith('/queue-next '): return self.queue_next(cmd.replace('/queue-next ', '').strip())
        if cmd == '/queue-run-next': return self.queue_run_next()
        if cmd.startswith('/queue-run-next '): return self.queue_run_next(cmd.replace('/queue-run-next ', '').strip())
        if cmd.startswith('/queue-run '): return self.queue_run_task(cmd.replace('/queue-run ', '').strip())
        if cmd.startswith('/queue-update '):
            parts = cmd.replace('/queue-update ', '').split(' ', 2)
            if len(parts) >= 2:
                note = parts[2] if len(parts) == 3 else ""
                return self.queue_update(parts[0], parts[1], note)
            return "Uso: /queue-update <id> <status> [nota]"
        
        if cmd == '/audit': return self.audit_project()
        if cmd == '/install':
            blocked = self._guard_action("install", {"command": cmd, "summary": "Instalar dependencias"})
            if blocked: return blocked
            return self.install_dependencies()
        if cmd == '/agents': return self.subagents.list_agents()
        if cmd == '/memory': return f"🧠 {self.memory.get_context_prompt(self.current_dir.name)}"
        
        if cmd.startswith('/delegate '):
            parts = cmd.replace('/delegate ', '').split(' ', 1)
            if len(parts) == 2:
                agent_name, task = parts
                return self.subagents.delegate(task.strip('"'), agent_name)
            return "Uso: /delegate [auditor|coder|debugger...] \"tarea\""
        
        if cmd.startswith('/project '): return self.switch_project(cmd.replace('/project ', '').strip())
        if cmd.startswith('/read '): return self._read_file(cmd.replace('/read ', '').strip())
        if cmd.startswith('/ls'): return self._list_dir()
        if cmd.startswith('/run '):
            blocked = self._guard_action("shell", {"command": cmd, "shell": cmd.replace('/run ', '').strip()})
            if blocked: return blocked
            return self._run_command(cmd.replace('/run ', '').strip())
        
        if cmd == '/init-business': return self.init_business_project()
        if cmd == '/define-niche': return self.define_niche()
        if cmd == '/create-mvp': return self.create_mvp_product()
        if cmd == '/setup-store': return self.setup_store()
        if cmd == '/generate-content': return self.generate_content_batch()
        if cmd == '/dashboard': return self.track_metrics()
        if cmd == '/add-task': return "Uso: /add-task \"tarea\" alta/media/baja"
        if cmd.startswith('/add-task '):
            parts = cmd.replace('/add-task ', '').strip('"').split()
            if len(parts) >= 1:
                task = ' '.join(parts[:-1]) if len(parts) > 1 else parts[0]
                priority = parts[-1] if parts[-1] in ["alta", "media", "baja"] else "media"
                return self.add_task(task, priority)
            return "Error en formato"
        if cmd == '/tasks': return self.list_tasks()
        if cmd.startswith('/complete-task '):
            try:
                idx = int(cmd.replace('/complete-task ', ''))
                return self.complete_task(idx)
            except:
                return "❌ Usá: /complete-task <número>"
        
        if cmd == '/gumroad-publish':
            blocked = self._guard_action("publish", {"command": cmd, "summary": "Publicar producto en Gumroad"})
            if blocked: return blocked
            return self.publish_to_gumroad()
        if cmd == '/gumroad-sales': return self.check_gumroad_sales()
        if cmd == '/gumroad-list': return self.list_gumroad_products()
        
        if cmd == '/autonomous-start':
            blocked = self._guard_action("autonomous_start", {"command": cmd, "summary": "Iniciar modo autonomo"})
            if blocked: return blocked
            return self.autonomous_engine.start_autonomous_mode(interval_minutes=30)
        if cmd == '/autonomous-stop':
            return self.autonomous_engine.stop_autonomous_mode()
        if cmd == '/autonomous-status':
            return self.autonomous_engine.get_status()
        if cmd == '/autonomous-now':
            self.autonomous_engine.run_cycle()
            return "✅ Ciclo autónomo ejecutado"
        
        if not self.client: return "⚠️ Configurá API_KEY en .env"

        context = f"Directorio: {self.current_dir}"
        system = f"""Sos un asistente experto.
{context}
Fecha: {CURRENT_DATE}
Puedes delegar a sub-agentes.
Respondé en español, técnico y conciso."""
        
        self.history.append({"role": "user", "content": user_input})
        try:
            res = self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": system}, *self.history[-8:]], max_tokens=1500)
            ans = res.choices[0].message.content
            self.history.append({"role": "assistant", "content": ans})
            self._save_history()
            return ans
        except Exception as e:
            return f"❌ Error: {e}"
