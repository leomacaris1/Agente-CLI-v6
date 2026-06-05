from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class ProjectProfile:
    name: str
    path: Path
    mission: str
    autonomy_notes: List[str] = field(default_factory=list)
    sensitive_actions: List[str] = field(default_factory=list)
    allowed_without_approval: List[str] = field(default_factory=list)


def build_project_profiles(project_paths: Dict[str, Path]) -> Dict[str, ProjectProfile]:
    profiles = {
        "agent": ProjectProfile(
            name="agent",
            path=project_paths["agent"],
            mission="Desarrollar el agente personal que orquesta proyectos, permisos, memoria y canales de control.",
            allowed_without_approval=["read", "list", "analysis", "draft"],
            sensitive_actions=["shell", "install", "autonomous_start", "deploy", "publish"],
            autonomy_notes=[
                "Priorizar seguridad, trazabilidad y rollback antes que velocidad.",
                "No modificar credenciales ni borrar historial sin aprobacion directa.",
            ],
        ),
        "mmnexus": ProjectProfile(
            name="mmnexus",
            path=project_paths["mmnexus"],
            mission="Operar y evolucionar MMNexus como producto/plataforma principal.",
            allowed_without_approval=["read", "list", "analysis", "draft"],
            sensitive_actions=["deploy", "external_message", "database", "shell", "install"],
            autonomy_notes=[
                "Puede proponer features, auditorias y PRs.",
                "Deploy, cambios de datos o comunicacion publica requieren aprobacion.",
            ],
        ),
        "fabrica": ProjectProfile(
            name="fabrica",
            path=project_paths["fabrica"],
            mission="Crear pipelines de productos digitales desde idea hasta paquete publicable.",
            allowed_without_approval=["read", "list", "analysis", "draft", "content_generation"],
            sensitive_actions=["publish", "spend", "external_message", "price_change", "deploy"],
            autonomy_notes=[
                "Puede generar borradores, maquetas, launch kits y reportes.",
                "Publicar, cambiar precios o enviar contenido comercial requiere aprobacion.",
            ],
        ),
    }
    return profiles
