# agent.py — Agent CLI v5 + Negocio Digital Autónomo
import os
import subprocess
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from urllib.parse import quote

from openai import OpenAI
from dotenv import load_dotenv

from memory import MemoryBank
from subagents import SubAgentRegistry

load_dotenv()
CURRENT_DATE = datetime.now().strftime('%d de %B de %Y')

class Agent:
    def __init__(self):
        self.model = os.getenv("MODEL", "meta-llama/llama-3.1-70b-instruct")
        self.api_key = os.getenv("API_KEY")
        self.api_base = "https://openrouter.ai/api/v1"
        
        if not self.api_key:
            print("⚠️ Error: No se encontró API_KEY en .env")
            self.client = None
        else:
            self.client = OpenAI(base_url=self.api_base, api_key=self.api_key)
            
        self.current_dir = Path.cwd()
        self.projects = {
            'mmnexus': Path(os.getenv("MMNEXUS_PATH", "C:/code/mmnexus-hub")),
            'fabrica': Path(os.getenv("FABRICA_PATH", "C:/code/fabrica"))
        }
        self.history = []
        self.memory = MemoryBank()
        self.subagents = SubAgentRegistry(self)
        self._load_history()

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

    # === Herramientas Básicas ===
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

    # === Telegram ===
    def _send_telegram(self, msg):
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            if not token or not chat_id: return "⚠️ Telegram no configurado"
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=10)
            return "✅ Enviado" if r.status_code == 200 else f"❌ {r.text}"
        except Exception as e: return f"❌ Error Telegram: {e}"

    # === Web Scraping ===
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

    # === Funciones de Agentes Especializados ===
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
        report += ["\n---\n*Agent CLI v5*"]
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
            os.chdir(self.current_dir)
            self.history = []
            return f"📁 Proyecto: {name}\n📍 {self.current_dir}"
        return f"❌ Proyectos: {', '.join(self.projects.keys())}"

    # === MÓDULO: NEGOCIO DIGITAL AUTÓNOMO ===
    def init_business_project(self):
        print("🚀 Inicializando negocio digital...")
        project_dir = Path.home() / "Desktop" / "Digital-Business"
        if not project_dir.exists():
            project_dir.mkdir(parents=True)
            (project_dir / "assets").mkdir(exist_ok=True)
            (project_dir / "content").mkdir(exist_ok=True)
            (project_dir / "analytics").mkdir(exist_ok=True)
            (project_dir / "social-media").mkdir(exist_ok=True)
            (project_dir / "products").mkdir(exist_ok=True)
            (project_dir / "reports").mkdir(exist_ok=True)
        
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

    # === Router Principal v5 ===
    def talk(self, user_input):
        if not self.client: return "⚠️ Configurá API_KEY en .env"
        
        cmd = user_input.strip()
        
        # Comandos directos
        if cmd == '/audit': return self.audit_project()
        if cmd == '/install': return self.install_dependencies()
        if cmd == '/agents': return self.subagents.list_agents()
        if cmd == '/memory': return f"🧠 {self.memory.get_context_prompt(self.current_dir.name)}"
        
        # Delegación
        if cmd.startswith('/delegate '):
            parts = cmd.replace('/delegate ', '').split(' ', 1)
            if len(parts) == 2:
                agent_name, task = parts
                return self.subagents.delegate(task.strip('"'), agent_name)
            return "Uso: /delegate [auditor|coder|debugger...] \"tarea\""
        
        if cmd.startswith('/project '): return self.switch_project(cmd.replace('/project ', '').strip())
        if cmd.startswith('/read '): return self._read_file(cmd.replace('/read ', '').strip())
        if cmd.startswith('/ls'): return self._list_dir()
        if cmd.startswith('/run '): return self._run_command(cmd.replace('/run ', '').strip())
        
        # Negocio Digital
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
        
        # Chat normal
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