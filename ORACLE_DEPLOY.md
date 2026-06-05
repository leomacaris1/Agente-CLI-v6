# Oracle Cloud deployment

Guia para correr el agente 24/7 en una instancia Ubuntu ARM de Oracle Cloud.

## 1. Crear instancia

Recomendado:

- Shape: ARM Ampere
- CPU: 4 OCPU
- RAM: 24 GB
- OS: Ubuntu 22.04 o 24.04
- Disco: 100 GB si vas a clonar varios proyectos

## 2. Preparar repos

```bash
sudo mkdir -p /opt/leoprojects
sudo chown -R "$USER":"$USER" /opt/leoprojects
cd /opt/leoprojects

git clone <agent-repo-url> agent-cli-v4-fresh
git clone <mmnexus-repo-url> mmnexus-hub
git clone <fabrica-repo-url> fabrica-productos-digitales
```

## 3. Bootstrap

```bash
cd /opt/leoprojects/agent-cli-v4-fresh
bash deploy/bootstrap_oracle.sh
```

Editar `.env`:

```bash
nano .env
```

Variables importantes:

```text
API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
MMNEXUS_PATH=/opt/leoprojects/mmnexus-hub
FABRICA_PATH=/opt/leoprojects/fabrica-productos-digitales
AGENT_STATE_DIR=/opt/leoprojects/agent-cli-v4-fresh/.agent_state
```

## 4. Probar manualmente

```bash
source .venv/bin/activate
python test_agent.py
python -c "from agent import Agent; a=Agent(); print(a.talk('/tg-status'))"
python -c "from agent import Agent; a=Agent(); print(a.talk('/daemon-status'))"
```

## 5. Instalar systemd services

```bash
sudo cp deploy/systemd/agent-daemon.service /etc/systemd/system/
sudo cp deploy/systemd/agent-telegram.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable agent-daemon agent-telegram
sudo systemctl start agent-daemon agent-telegram
```

Ver logs:

```bash
journalctl -u agent-daemon -f
journalctl -u agent-telegram -f
```

Reiniciar:

```bash
sudo systemctl restart agent-daemon agent-telegram
```

## 6. Variables operativas

```text
AGENT_DAEMON_INTERVAL_SECONDS=300
AGENT_DAEMON_DIGEST_EVERY=12
AGENT_DAEMON_PROJECT=
TELEGRAM_ALLOW_RUN=true
AGENT_WRITE_PROJECT_OUTPUTS=false
```

Recomendacion inicial:

- Mantener `AGENT_WRITE_PROJECT_OUTPUTS=false`.
- Mantener `TELEGRAM_ALLOW_RUN=true` solo si queres ejecutar tareas seguras desde Telegram.
- No configurar Gumroad hasta que el flujo de aprobaciones este probado en servidor.

## 7. Ollama + Qwen

Para instalar Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b
```

Nota: el agente actual usa OpenRouter via `API_KEY`. Ollama queda preparado para una siguiente fase donde agreguemos proveedor local/fallback.

## 8. Seguridad

- No commitear `.env`.
- Restringir SSH con key pair.
- Usar un usuario no-root para correr el repo.
- Revisar `/approvals` antes de aprobar publicaciones, deploys o comandos.
- Mantener acciones destructivas bloqueadas por politica.
