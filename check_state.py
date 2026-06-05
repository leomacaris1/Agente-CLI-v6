from pathlib import Path
import json

project_dir = Path.home() / "Desktop" / "Digital-Business"
state_file = project_dir / "autonomous_state.json"

print(f"📁 Directorio: {project_dir}")
print(f"Existe: {project_dir.exists()}")

if state_file.exists():
    with open(state_file, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    print(f"\n📋 Estado actual:")
    print(f"Tareas en cola: {len(state.get('queue', []))}")
    print(f"Última acción: {state.get('last_action')}")
    
    pending = [t for t in state.get('queue', []) if t.get('status') == 'pending']
    print(f"\n✅ Tareas pendientes ({len(pending)}):")
    for task in pending:
        print(f"  - {task.get('task')}")
else:
    print("❌ No existe autonomous_state.json")
    print("📝 Ejecutá /init-business en el agente para crearlo")

# Verificar .env
env_file = Path("C:/agent-cli-v4/.env")
if env_file.exists():
    content = env_file.read_text()
    print(f"\n📄 Telegram configurado: {'TELEGRAM_BOT_TOKEN' in content}")
    print(f"📄 Gumroad configurado: {'GUMROAD_TOKEN' in content}")