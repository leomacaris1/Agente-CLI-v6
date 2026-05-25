# memory.py
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Callable

class MemoryBank:
    def __init__(self):
        self.memory_file = Path.home() / ".agent_memory.json"
        self.data = self.load_memory()
        self._runtime_skills: Dict[str, Callable] = {}
    
    def load_memory(self) -> dict:
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"projects": {}, "skills": [], "preferences": {"code_style": "typescript"}, "created_at": datetime.now().isoformat()}
    
    def add_skill_meta(self, name: str, description: str, triggers: List[str]):
        if "skills" not in self.data:
            self.data["skills"] = []
        if not any(s["name"] == name for s in self.data["skills"]):
            self.data["skills"].append({"name": name, "description": description, "triggers": triggers, "registered_at": datetime.now().isoformat()})
            self.save_memory()
    
    def register_skill(self, name: str, description: str, triggers: List[str], handler: Callable):
        self.add_skill_meta(name, description, triggers)
        self._runtime_skills[name] = handler
    
    def get_matching_skill(self, user_input: str) -> Optional[Dict]:
        for skill in self.data.get("skills", []):
            if any(t in user_input.lower() for t in skill["triggers"]):
                return skill
        return None
    
    def execute_skill(self, name: str, **kwargs):
        if name in self._runtime_skills:
            return self._runtime_skills[name](**kwargs)
        return f"❌ Skill '{name}' no registrada"
    
    def get_context_prompt(self, project_name: str) -> str:
        skills = "\n".join([f"- {s['name']}: {s['description']}" for s in self.data.get("skills", [])[-10:]])
        prefs = self.data.get("preferences", {})
        return f"""**🧠 MEMORIA**
**Habilidades:**
{skills if skills else "*Ninguna*"}

**Preferencias:**
- Estilo: {prefs.get('code_style', 'No definido')}"""
    
    def save_memory(self):
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)