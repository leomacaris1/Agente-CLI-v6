<<<<<<< HEAD
# subagents.py
=======
# subagents.py — Registry de sub-agentes especializados con Tool Calling
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass

@dataclass
class SubAgent:
    name: str
    description: str
    tools: List[str]
    handler: Callable
    keywords: List[str]
    priority: int = 0
    native_tools: List[str] = None

class SubAgentRegistry:
    def __init__(self, main_agent):
        self.agents: Dict[str, SubAgent] = {}
        self.main = main_agent
        self._register_defaults()
    
    def _register_defaults(self):
<<<<<<< HEAD
        self.register("auditor", "Analiza código y seguridad", ["read_file", "run_command"], self.main.audit_project, ["auditar", "vulnerabilidad", "seguridad"])
        self.register("coder", "Genera código TypeScript/React", ["write_file", "read_file"], self.main.generate_code_task, ["generar", "crear", "componente"])
        self.register("researcher", "Busca documentación", ["web_search"], self.main.scrape_docs, ["buscar", "documentación", "docs"])
        self.register("deps", "Gestiona dependencias npm", ["run_command"], self.main.install_dependencies, ["npm", "instalar", "dependencias"])
        self.register("deployer", "Deploy en Vercel/Netlify", ["write_file"], self.main.deploy_project, ["deploy", "vercel", "subir"])
        self.register("debugger", "Debugging asistido", ["read_file"], self.main.debug_code, ["error", "bug", "falla"])
        self.register("documenter", "Documentación automática", ["write_file"], self.main.document_project, ["documentar", "readme"])
    
    def register(self, name, description, tools, handler, keywords):
        self.agents[name] = SubAgent(name, description, tools, handler, keywords)
=======
        self.register("auditor",
            description="Analiza código, dependencias y seguridad",
            tools=["read_file", "run_command", "audit_dependencies"],
            handler=self.main.audit_project,
            keywords=["auditar", "vulnerabilidad", "seguridad", "dependencia", "npm audit"],
            priority=1,
            native_tools=["read_file", "list_directory", "run_command", "audit_project"]
        )
        self.register("coder",
            description="Genera componentes, funciones, hooks con TypeScript/React",
            tools=["read_file", "write_file", "run_command"],
            handler=self.main.generate_code_task,
            keywords=["generar", "crear", "componente", "función", "hook", "código", "archivo", "módulo"],
            priority=2,
            native_tools=["read_file", "write_file", "generate_code", "list_directory"]
        )
        self.register("researcher",
            description="Busca documentación, tendencias y mejores prácticas",
            tools=["web_search", "scrape_docs", "write_file"],
            handler=self.main._scrape_docs,
            keywords=["buscar", "documentación", "tendencia", "mejor práctica", "docs", "investigar"],
            priority=3,
            native_tools=["search_web", "write_file", "read_file"]
        )
        self.register("deps",
            description="Instala, actualiza y audita dependencias npm/yarn",
            tools=["run_command", "audit_dependencies"],
            handler=self.main.install_dependencies,
            keywords=["instalar", "npm", "yarn", "dependencia", "actualizar", "package.json", "pnpm"],
            priority=4,
            native_tools=["run_command", "install_dependencies", "read_file"]
        )
        self.register("deployer",
            description="Configura despliegue en Vercel, Netlify o GitHub Pages",
            tools=["read_file", "write_file", "run_command"],
            handler=self.main.deploy_preview,
            keywords=["desplegar", "deploy", "vercel", "netlify", "preview", "producción", "build"],
            priority=5,
            native_tools=["read_file", "write_file", "run_command"]
        )
        self.register("debugger",
            description="Ayuda a debuggear errores y problemas en el código",
            tools=["read_file", "run_command", "write_file"],
            handler=self.main._debug_task,
            keywords=["error", "bug", "debug", "falla", "problema", "no funciona", "crash"],
            priority=6,
            native_tools=["read_file", "run_command", "write_file", "list_directory"]
        )
        self.register("documenter",
            description="Genera documentación, READMEs y comentarios",
            tools=["read_file", "write_file"],
            handler=self.main._document_task,
            keywords=["documentar", "readme", "comentarios", "doc", "instrucciones"],
            priority=7,
            native_tools=["read_file", "write_file", "list_directory"]
        )
    
    def register(self, name: str, description: str, tools: List[str], handler: Callable, keywords: List[str], priority: int = 0, native_tools: List[str] = None):
        self.agents[name] = SubAgent(name, description, tools, handler, keywords, priority, native_tools or [])
    
    def select_agent(self, task: str) -> Optional[SubAgent]:
        task_lower = task.lower()
        matches = []
        for agent in self.agents.values():
<<<<<<< HEAD
            score = sum(1 for kw in agent.keywords if kw in task_lower)
            if score > 0:
                matches.append((agent, score))
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[0][0] if matches else None
=======
            match_count = sum(1 for kw in agent.keywords if kw in task_lower)
            if match_count > 0:
                matches.append((match_count, -agent.priority, agent))
        if matches:
            matches.sort(key=lambda x: (-x[0], x[1]))
            return matches[0][2]
        return None
    
    def delegate(self, task: str, agent_name: Optional[str] = None, **kwargs) -> str:
        if agent_name and agent_name in self.agents:
            agent = self.agents[agent_name]
            print(f"🤖 Delegando a {agent.name}: {task}")
            return agent.handler(task=task, **kwargs)
        agent = self.select_agent(task)
        if agent:
<<<<<<< HEAD
            return f"🤖 Delegando a {agent.name}: {agent.description}\n\n" + agent.handler(task=task, **kwargs)
        return self.main.talk(task)
    
    def list_agents(self) -> str:
        lines = ["🤖 **Sub-Agentes:**\n"]
        for name, agent in self.agents.items():
            lines.append(f"**{name}**: {agent.description}")
        return "\n".join(lines)
=======
            print(f"🤖 Auto-delegando a {agent.name}: {task}")
            return agent.handler(task=task, **kwargs)
        return f"🤔 No encontré un sub-agente específico para: '{task}'\n\n" + self.main.talk(task)
    
    def list_agents(self) -> str:
        lines = ["🤖 **Sub-Agentes disponibles**:\n"]
        for name, agent in sorted(self.agents.items(), key=lambda x: x[1].priority):
            lines.append(f"### `{name}`")
            lines.append(f"{agent.description}")
            lines.append(f"🔧 Herramientas: `{', '.join(agent.tools)}`")
            if agent.native_tools:
                lines.append(f"⚡ Native Tools: `{', '.join(agent.native_tools[:5])}`")
            lines.append(f"🎯 Keywords: `{', '.join(agent.keywords[:5])}`\n")
        return "\n".join(lines)
    
    def get_agent_tools(self, agent_name: str) -> List[str]:
        if agent_name in self.agents:
            return self.agents[agent_name].native_tools
        return []
