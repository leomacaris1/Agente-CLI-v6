# 🦅 Agent CLI v6 — con Tool Calling Nativo

**Agente Inteligente con Sub-Agentes Especializados y Tool Calling Nativo para Automatizar Proyectos de Desarrollo**

Un asistente impulsado por IA que se integra en tu flujo de trabajo, capaz de auditar proyectos, generar código, debuggear errores, documentar y notificarte por Telegram. Ahora con **tool calling nativo** que permite a la IA decidir automáticamente qué herramientas usar.

---

## ✨ Novedades v6

### 🔥 Tool Calling Nativo
- **9 herramientas nativas** disponibles para la IA
- La IA decide automáticamente qué herramienta usar según el contexto
- Ejecución multi-paso con retroalimentación automática
- Historial enriquecido con tool calls y resultados

### 🤖 Sub-Agentes Mejorados
- Cada sub-agente tiene herramientas nativas específicas
- Auto-selección inteligente por keywords + contexto
- Sistema de prioridades optimizado

### 🛠️ Herramientas Disponibles
| Herramienta | Descripción |
|------------|-------------|
| `read_file` | Lee archivos del proyecto |
| `write_file` | Escribe contenido en archivos |
| `list_directory` | Lista archivos y directorios |
| `run_command` | Ejecuta comandos en terminal |
| `search_web` | Busca información en internet |
| `send_telegram` | Envía notificaciones a Telegram |
| `audit_project` | Auditoría completa automática |
| `install_dependencies` | Instala dependencias npm/yarn/pnpm |
| `generate_code` | Genera código TypeScript/React |

---

## 🤖 Sub-Agentes Disponibles

| Agente | Descripción | Native Tools |
|--------|-------------|--------------|
| **auditor** | Analiza código, dependencias y seguridad | read_file, list_directory, run_command, audit_project |
| **coder** | Genera componentes, funciones, hooks TypeScript/React | read_file, write_file, generate_code, list_directory |
| **researcher** | Busca documentación y mejores prácticas | search_web, write_file, read_file |
| **deps** | Instala y actualiza dependencias npm/yarn/pnpm | run_command, install_dependencies, read_file |
| **deployer** | Configura despliegue en Vercel/Netlify | read_file, write_file, run_command |
| **debugger** | Ayuda a debuggear errores y problemas | read_file, run_command, write_file, list_directory |
| **documenter** | Genera documentación y READMEs | read_file, write_file, list_directory |

---

## 📋 Requisitos Previos

- Python 3.10 o superior
- Node.js y npm (para proyectos a auditar)
- Cuenta en [OpenRouter](https://openrouter.ai/) (API Key gratuita)
- Bot de Telegram (opcional, para notificaciones)

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/leomacaris1/agente-cli-v4-fresh.git
cd agente-cli-v4-fresh
```

### 2. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Creá un archivo `.env` en la raíz del proyecto:

```env
API_KEY=tu_api_key_de_openrouter
MODEL=meta-llama/llama-3.1-70b-instruct
TELEGRAM_BOT_TOKEN=tu_token_opcional
TELEGRAM_CHAT_ID=tu_chat_id_opcional
MMNEXUS_PATH=C:/code/mmnexus-hub
FABRICA_PATH=C:/code/fabrica
```

⚠️ **Importante:**
- Conseguí tu API Key en: https://openrouter.ai/keys
- **NUNCA** subas el archivo `.env` a GitHub

---

## 📖 Uso

### Iniciar el agente

```bash
python web_ui.py
```

Esto iniciará la interfaz web en: `http://127.0.0.1:7862`

### Testear sin UI

```bash
python test_agent.py
```

---

## 💬 Comandos Disponibles

### Comandos Principales

| Comando | Descripción |
|---------|------------|
| `/audit` | Auditoría completa del proyecto + reporte en Telegram |
| `/install` | Ejecuta `npm install` automáticamente |
| `/audit-deps` | Analiza vulnerabilidades con `npm audit` |
| `/fix` | Corrige vulnerabilidades con `npm audit fix` |
| `/deploy` | Genera instrucciones de deploy |
| `/agents` | Lista todos los sub-agentes disponibles |
| `/delegate <agente> <tarea>` | Delega tarea a sub-agente específico |
| `/project <nombre>` | Cambia entre proyectos configurados |
| `/read <archivo>` | Lee el contenido de un archivo |
| `/ls` | Lista archivos del directorio actual |
| `/run <comando>` | Ejecuta un comando en terminal |
| `/search <tema>` | Busca información en internet |
| `/memory` | Muestra la memoria y habilidades del agente |

---

## 💡 Ejemplos de Uso

### 1. Tool Calling Automático

El agente ahora usa tool calling nativo. Cuando le pedís algo, la IA decide automáticamente qué herramientas usar:

```
"Leé el package.json y decime las dependencias"
→ Usa: read_file → analiza → responde

"Creá un componente Button.tsx"
→ Usa: generate_code → write_file → responde

"Auditá el proyecto"
→ Usa: list_directory → read_file → audit_project → responde
```

### 2. Usar sub-agentes específicos

```bash
# Delegar generación de código
/delegate coder crear componente Button con TypeScript

# Delegar debugging
/delegate debugger error en Component.tsx línea 45

# Delegar documentación
/delegate documenter generar README para este proyecto

# Delegar instalación
/delegate deps instalar todas las dependencias
```

### 3. Auto-delegación inteligente

El agente detecta automáticamente qué sub-agente usar según tu mensaje:

```
# Auto-delega al agentedeps
"Necesito instalar las dependencias"

# Auto-delega al agentecoder
"Crear un hook useAuth con TypeScript"

# Auto-delega al agentedebugger
"Tengo un error en la línea 30 de App.tsx"

# Auto-delega al agentedocumenter
"Documentar este módulo"
```

### 4. Comandos directos

```bash
/audit          # Auditoría completa
/install        # npm install
/deploy         # Instrucciones de deploy
/memory         # Ver memoria del agente
```

---

## 🏗️ Estructura del Proyecto

```
/workspace/
├── agent.py          # Agente principal + Tool Calling Nativo
├── subagents.py      # Registry de sub-agentes + native tools
├── memory.py         # Memoria persistente + skills dinámicas
├── web_ui.py         # Interfaz web con Gradio
├── test_agent.py     # Script de testing
├── requirements.txt  # Dependencias de Python
└── README.md         # Este archivo
```

---

## 🔐 Seguridad

### Archivos sensibles

El archivo `.env` contiene:
- API Keys de OpenRouter
- Tokens de Telegram
- Rutas locales de proyectos

**NUNCA** debe subirse a GitHub. El archivo `.gitignore` ya está configurado para excluirlo.

### Rotación de claves

Si por error subiste tus claves a GitHub:
1. Revocalas inmediatamente en OpenRouter
2. Generá nuevas claves
3. Actualizá tu `.env`

---

## 🧠 Memoria Persistente

El agente recuerda:
- **Skills registradas**: Habilidades que aprende con el uso
- **Lecciones por proyecto**: Experiencias y soluciones aplicadas
- **Preferencias**: Estilo de código, framework favorito, etc.

La memoria se guarda en `~/.agent_memory.json`

---

## 🔄 Flujo de Tool Calling

1. **Usuario** envía un mensaje
2. **IA** analiza el mensaje y decide si necesita herramientas
3. Si necesita herramientas:
   - Devuelve **tool calls** con nombres y argumentos
   - El agente **ejecuta** cada herramienta
   - Los resultados se **agregan al historial**
   - La IA **vuelve a llamar** para generar respuesta final
4. **Respuesta** se envía al usuario

### Ejemplo de flujo:

```
Usuario: "Leé el package.json y mostrame las dependencias"

IA (primera llamada):
  tool_calls: [{
    name: "read_file",
    arguments: {path: "package.json"}
  }]

Agente ejecuta: read_file("package.json")
Resultado: {"name": "mi-proyecto", "dependencies": {...}}

IA (segunda llamada con resultado):
  "Las dependencias del proyecto son: ..."

Usuario recibe respuesta completa
```

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Hacé un fork del repositorio
2. Creá una rama (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add some AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Abrí un Pull Request

---

## 📝 Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE).

---

## 🙏 Agradecimientos

- **OpenRouter** por proveer la API de IA con tool calling
- **Gradio** por la interfaz web
- **Telegram** por las notificaciones
- **DuckDuckGo Search** para búsquedas web

---

## 📞 Soporte

Si tenés problemas o sugerencias, creá un issue en el repositorio.

---

**Desarrollado con ❤️ por leomacaris1**

*Versión 6.0 — Con Tool Calling Nativo*
