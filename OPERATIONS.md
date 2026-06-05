# Operacion del agente

## Flujo base

1. Proponer una tarea:

```text
/propose-task generar portada para ebook de la fabrica
```

2. Revisar la cola:

```text
/queue
/queue queued
/queue needs_approval
```

3. Ver la proxima tarea ejecutable:

```text
/queue-next
/queue-next fabrica
```

4. Revisar aprobaciones pendientes:

```text
/approvals
```

5. Aprobar o rechazar:

```text
/approve <id>
/reject <id>
```

6. Ejecutar la proxima tarea segura:

```text
/queue-run-next
/queue-run-next fabrica
/queue-run <task_id>
```

7. Cambiar estado manualmente:

```text
/queue-update <task_id> running
/queue-update <task_id> done "resultado resumido"
/queue-update <task_id> failed "motivo"
```

## Estados de tareas

- `queued`: lista para ejecutar.
- `needs_approval`: espera autorizacion.
- `running`: en ejecucion.
- `done`: completada.
- `failed`: fallo.
- `rejected`: rechazada.

## Ejecucion segura actual

El runner ejecuta solo acciones de bajo riesgo:

- `read`
- `analysis`
- `draft`
- `content_generation`

Estas acciones generan artefactos locales en:

```text
.agent_state/outputs/<proyecto>/
```

## Skills internas actuales

- `creator` para `fabrica`: genera paquete de producto digital con `manifest.md`, `cover_prompt.md`, `mockup.md`, `launch_kit.md` y `qa_checklist.md`.
- `auditor`: genera snapshot/auditoria inicial del proyecto con senales de stack y archivos principales.
- `planner`: genera plan operativo seguro para tareas de borrador.
- `researcher`: genera snapshot de lectura cuando la accion es `read`.

La cola esta pensada para correr desde un unico proceso/daemon. Evitar ejecutar varios procesos del agente escribiendo la cola al mismo tiempo hasta migrarla a SQLite o un backend transaccional.

Para escribir outputs dentro de cada repositorio, configurar:

```text
AGENT_WRITE_PROJECT_OUTPUTS=true
```

## Reglas actuales

- La generacion de borradores y contenido para la fabrica puede quedar en cola sin aprobacion.
- Publicar, desplegar, ejecutar comandos o iniciar modo autonomo requiere aprobacion.
- Acciones destructivas quedan bloqueadas por politica.

## Telegram

Comandos locales relacionados:

```text
/tg-help
/tg-diagnose
/tg-status
/tg-send-status
/secret-check
/tg-handle <comando>
```

Para correr polling en servidor:

```text
python telegram_poll.py
```

Variables necesarias:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_ALLOW_RUN=true
```

Seguridad:

- Solo se procesan mensajes cuyo chat coincida con `TELEGRAM_CHAT_ID`.
- Si `/tg-send-status` devuelve `chat not found`, abrir el bot en Telegram, enviar `/start` y ejecutar `/tg-diagnose`.
- Si `/tg-diagnose` muestra otro `chat_id` en `getUpdates`, usar ese valor en `TELEGRAM_CHAT_ID`.
- Desde Telegram se permite un subconjunto de comandos operativos: cola, aprobaciones, propuestas, policy y status.
- Comandos como `/run`, `/install`, `/gumroad-publish` o `/autonomous-start` no se aceptan directamente por Telegram; deben pasar por propuesta/aprobacion.
- `TELEGRAM_ALLOW_RUN=false` desactiva `/queue-run-next` desde Telegram.

## Daemon 24/7

Comandos locales:

```text
/daemon-status
/daemon-once
/daemon-once fabrica
/daemon-send-digest
/daily-brief
/send-daily-brief
```

Para correr el loop 24/7:

```text
python agent_daemon.py
```

Variables:

```text
AGENT_DAEMON_INTERVAL_SECONDS=300
AGENT_DAEMON_DIGEST_EVERY=12
AGENT_DAEMON_PROJECT=
```

Notas:

- El daemon ejecuta una tarea `queued` por ciclo.
- Solo ejecuta tareas que el runner considera seguras.
- Las acciones sensibles quedan como `needs_approval`.
- Para usarlo con Telegram, correr `telegram_poll.py` en otro proceso o integrarlo luego en un supervisor.
- En Oracle Cloud conviene correr ambos procesos con `systemd`: uno para `agent_daemon.py` y otro para `telegram_poll.py`.

## Runner local en Windows

Mientras Oracle Cloud no este listo, se puede dejar el agente corriendo con Task Scheduler:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\install_local_daemon_task.ps1
powershell -ExecutionPolicy Bypass -File .\deploy\windows\install_telegram_poll_task.ps1
```

Variables opcionales:

```text
AGENT_WINDOWS_TASK_NAME=LeoProjects-Agent-Daemon
AGENT_TELEGRAM_TASK_NAME=LeoProjects-Agent-Telegram
AGENT_PYTHON=python
```

Para quitar la tarea:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\windows\uninstall_local_daemon_task.ps1
powershell -ExecutionPolicy Bypass -File .\deploy\windows\uninstall_telegram_poll_task.ps1
```

Si Task Scheduler esta bloqueado por permisos, usar los launchers sin admin:

```powershell
.\deploy\windows\start_agent_daemon.cmd
.\deploy\windows\start_telegram_poll.cmd
```

Logs:

```text
.agent_state/logs/agent_daemon.log
.agent_state/logs/telegram_poll.log
```

Chequeo de exposicion de secretos:

```text
python scripts/check_secret_exposure.py
/secret-check
```

El comando falla si detecta secretos reales en logs activos o lineas de comando de procesos.

## Tablero operativo

Comandos:

```text
/multi-status
/daily-brief
/send-daily-brief
```

`/daily-brief` resume:

- estado de los tres proyectos;
- cola y proxima tarea segura;
- aprobaciones pendientes;
- reglas de autonomia;
- politica economica;
- siguientes pasos recomendados.

## Repos de referencia

- El monitoreo diario activo cubre solo `agent`, `mmnexus` y `fabrica`.
- `mmnexus-hub-review` queda como sandbox/worktree de pruebas y no debe tratarse como repo primario de salud diaria salvo pedido explicito.

## Politica economica

Comandos:

```text
/budget
/budget-check <monto> <categoria> [descripcion]
```

Por defecto el agente tiene gasto preaprobado `0`. Eso significa:

- puede planificar oportunidades de ingresos;
- puede preparar productos, contenido, landing pages y reportes;
- no puede gastar, publicar anuncios, comprar dominios ni activar servicios pagos sin aprobacion;
- cualquier presupuesto futuro debe configurarse explicitamente en `.agent_state/budget_policy.json`.
