# Politica de autonomia inicial

Este documento define que puede hacer el agente sin permiso y que debe pedir por Telegram o por la UI antes de avanzar.

## Niveles

### Nivel 0 - Observar
Permitido sin aprobacion:
- Leer archivos.
- Listar directorios.
- Consultar estado.
- Revisar metricas.
- Generar reportes.

### Nivel 1 - Proponer
Permitido sin aprobacion:
- Sugerir tareas.
- Priorizar backlog.
- Crear planes.
- Preparar prompts, briefs y borradores.

### Nivel 2 - Ejecutar sin riesgo alto
Permitido sin aprobacion por ahora:
- Generar contenido local.
- Crear archivos de trabajo en carpetas del proyecto.
- Actualizar dashboards internos.
- Preparar instrucciones de deploy.

### Nivel 3 - Requiere aprobacion
Debe pedir permiso:
- Ejecutar comandos de shell arbitrarios.
- Instalar dependencias.
- Iniciar modo autonomo.
- Publicar productos en Gumroad.
- Desplegar a produccion.
- Enviar mensajes externos bajo marca personal o comercial.
- Cambiar precios, landing pages o assets publicos.

### Nivel 4 - Bloqueado por defecto
No debe ejecutarse sin intervencion directa:
- Borrar archivos o carpetas de forma destructiva.
- Resetear git con perdida de cambios.
- Acciones irreversibles sobre bases de datos.
- Gastos, contrataciones o pagos.
- Cambios legales, fiscales o de credenciales.

## Comandos de aprobacion

- `/approvals`: lista aprobaciones pendientes.
- `/approve <id>`: aprueba y ejecuta una accion pendiente.
- `/reject <id>`: rechaza una accion pendiente.
- `/policy`: muestra esta politica resumida.

## Objetivo

La autonomia se aumenta por evidencia: primero el agente observa, luego propone, despues ejecuta tareas reversibles, y solo mas adelante opera proyectos completos con limites claros.
