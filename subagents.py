# subagents.py — Agent CLI v6 Registry
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass

@dataclass
class SubAgent:
    name: str
    description: str
    tools: List[str]
    handler: Callable
    keywords: List[str]

class SubAgentRegistry:
    def __init__(self, main_agent):
        self.agents: Dict[str, SubAgent] = {}
        self.main = main_agent
        self._register_defaults()
    
    def _register_defaults(self):
        # 1. Auditor
        self.register("auditor",
            description="Analiza código, dependencias y seguridad",
            tools=["read_file", "run_command", "audit_dependencies"],
            handler=self.main.audit_project,
            keywords=["auditar", "vulnerabilidad", "seguridad", "dependencia", "npm audit", "análisis"]
        )
        # 2. Coder
        self.register("coder",
            description="Genera componentes, funciones, hooks con TypeScript/React",
            tools=["read_file", "write_file", "run_command"],
            handler=self.main.generate_code_task,
            keywords=["generar", "crear", "componente", "función", "hook", "código", "implementar"]
        )
        # 3. Researcher
        self.register("researcher",
            description="Busca documentación, tendencias y mejores prácticas",
            tools=["web_search", "scrape_docs", "write_file"],
            handler=self.main.scrape_docs,
            keywords=["buscar", "documentación", "tendencia", "mejor práctica", "docs", "cómo"]
        )
        # 4. Deps Manager
        self.register("deps",
            description="Instala, actualiza y audita dependencias npm/yarn/pnpm",
            tools=["run_command", "audit_dependencies"],
            handler=self.main.install_dependencies,
            keywords=["instalar", "npm", "yarn", "pnpm", "dependencia", "actualizar", "package.json"]
        )
        # 5. Deployer
        self.register("deployer",
            description="Configura despliegue en Vercel, Netlify o GitHub Pages",
            tools=["read_file", "write_file", "run_command"],
            handler=self.main.deploy_project,
            keywords=["desplegar", "deploy", "vercel", "netlify", "preview", "producción", "subir"]
        )
        # 6. Debugger
        self.register("debugger",
            description="Ayuda a encontrar y corregir errores en el código",
            tools=["read_file", "run_command"],
            handler=self.main.debug_code,
            keywords=["error", "bug", "buggy", "falla", "debug", "arreglar", "fix error", "no funciona"]
        )
        # 7. Documenter
        self.register("documenter",
            description="Genera documentación automática (README, comentarios)",
            tools=["read_file", "write_file"],
            handler=self.main.document_project,
            keywords=["documentar", "readme", "comentarios", "explicar", "documentación"]
        )
    
    def register(self, name: str, description: str, tools: List[str], handler: Callable, keywords: List[str]):
        self.agents[name] = SubAgent(name, description, tools, handler, keywords)
    
    def select_agent(self, task: str) -> Optional[SubAgent]:
        task_lower = task.lower()
        matches = []
        
        for agent in self.agents.values():
            score = sum(1 for kw in agent.keywords if kw in task_lower)
            if score > 0:
                matches.append((agent, score))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[0][0] if matches else None
    
    def delegate(self, task: str, agent_name: Optional[str] = None, **kwargs) -> str:
        if agent_name and agent_name in self.agents:
            agent = self.agents[agent_name]
            return agent.handler(task=task, **kwargs)
        
        agent = self.select_agent(task)
        if agent:
            return f"🤖 **Delegando a {agent.name}:** {agent.description}\n\n" + agent.handler(task=task, **kwargs)
        
        return self.main.talk(task)
    
    def list_agents(self) -> str:
        lines = ["🤖 **Sub-Agentes Disponibles:**\n"]
        for name, agent in self.agents.items():
            lines.append(f"**{name}**: {agent.description}")
        return "\n".join(lines)