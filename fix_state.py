# fix_state.py - Genera el estado inicial del agente autónomo
import json
from pathlib import Path
from datetime import datetime

project_dir = Path.home() / "Desktop" / "Digital-Business"
state_file = project_dir / "autonomous_state.json"

# Aseguramos que la carpeta exista
project_dir.mkdir(parents=True, exist_ok=True)

# Definimos el plan de 30 días
state = {
    "queue": [
        {"task": "/define-niche", "priority": 1, "week": 1, "status": "pending"},
        {"task": "/create-mvp 'plantilla' 'nichos validados'", "priority": 2, "week": 1, "status": "pending"},
        {"task": "Generar contenido completo del producto: 'Planificador de Productividad Para Emprendedores'", "priority": 3, "week": 1, "status": "pending"},
        {"task": "/gumroad-publish", "priority": 1, "week": 1, "status": "pending"},
        {"task": "/generate-content 5 tiktok", "priority": 1, "week": 2, "status": "pending"},
        {"task": "/generate-content 5 instagram", "priority": 2, "week": 2, "status": "pending"},
        {"task": "/gumroad-sales", "priority": 1, "week": 3, "status": "pending"},
        {"task": "Analizar métricas y optimizar", "priority": 1, "week": 4, "status": "pending"}
    ],
    "last_action": None,
    "decision_count": 0,
    "updated": datetime.now().isoformat()
}

# Guardamos el archivo
with open(state_file, 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=2, ensure_ascii=False)

print("✅ autonomous_state.json creado correctamente.")
print("📂 Ubicación:", state_file)