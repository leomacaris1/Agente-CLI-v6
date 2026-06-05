from dataclasses import dataclass
from typing import Dict, List


@dataclass
class TaskRoute:
    project: str
    action_type: str
    worker: str
    confidence: float
    requires_approval: bool
    reason: str


class TaskRouter:
    """Deterministic project/task router for the personal agent."""

    PROJECT_KEYWORDS: Dict[str, List[str]] = {
        "agent": [
            "agente",
            "agent",
            "telegram",
            "autonomo",
            "autónomo",
            "orquestador",
            "ollama",
            "qwen",
            "servidor",
            "oracle",
        ],
        "mmnexus": [
            "mmnexus",
            "nexus",
            "hub",
            "plataforma",
        ],
        "fabrica": [
            "fabrica",
            "fábrica",
            "producto digital",
            "ebook",
            "curso",
            "video",
            "gumroad",
            "portada",
            "maqueta",
            "redes",
            "tiktok",
            "instagram",
            "launch kit",
        ],
    }

    ACTION_KEYWORDS: Dict[str, List[str]] = {
        "read": ["leer", "revisar", "ver", "listar", "mostrar", "inspeccionar"],
        "analysis": ["analizar", "auditar", "diagnosticar", "evaluar", "comparar"],
        "draft": ["proponer", "plan", "brief", "borrador", "diseñar", "especificar"],
        "content_generation": ["generar", "crear contenido", "escribir", "copy", "guion", "post", "ebook"],
        "shell": ["ejecutar", "correr", "run", "comando", "terminal"],
        "install": ["instalar", "npm install", "pip install", "dependencias"],
        "deploy": ["deploy", "desplegar", "produccion", "producción", "publicar app"],
        "publish": ["publicar", "gumroad", "subir producto", "lanzar"],
        "external_message": ["enviar email", "mandar mensaje", "publicar en redes", "telegram a cliente"],
        "spend": ["comprar", "pagar", "contratar", "gastar", "presupuesto"],
        "autonomous_start": ["iniciar autonomo", "modo autonomo", "24/7", "scheduler"],
    }

    WORKER_BY_ACTION = {
        "read": "researcher",
        "analysis": "auditor",
        "draft": "planner",
        "content_generation": "creator",
        "shell": "operator",
        "install": "deps",
        "deploy": "deployer",
        "publish": "publisher",
        "external_message": "marketer",
        "spend": "owner",
        "autonomous_start": "operator",
    }

    def __init__(self, project_profiles):
        self.project_profiles = project_profiles

    def route(self, task: str, current_project: str = "agent") -> TaskRoute:
        text = task.lower()
        project, project_score = self._score_project(text, current_project)
        action_type, action_score = self._score_action(text)
        profile = self.project_profiles.get(project)
        requires_approval = True

        if profile:
            if action_type in profile.allowed_without_approval:
                requires_approval = False
            if action_type in profile.sensitive_actions:
                requires_approval = True

        confidence = min(0.95, 0.45 + (project_score * 0.1) + (action_score * 0.08))
        reason = (
            f"Proyecto detectado por {project_score} coincidencias; "
            f"accion '{action_type}' por {action_score} coincidencias."
        )

        return TaskRoute(
            project=project,
            action_type=action_type,
            worker=self.WORKER_BY_ACTION.get(action_type, "generalist"),
            confidence=round(confidence, 2),
            requires_approval=requires_approval,
            reason=reason,
        )

    def _score_project(self, text: str, current_project: str):
        best_project = current_project if current_project in self.project_profiles else "agent"
        best_score = 0
        for project, keywords in self.PROJECT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > best_score:
                best_project = project
                best_score = score
        return best_project, best_score

    def _score_action(self, text: str):
        best_action = "draft"
        best_score = 0
        for action_type, keywords in self.ACTION_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > best_score:
                best_action = action_type
                best_score = score
        return best_action, best_score
