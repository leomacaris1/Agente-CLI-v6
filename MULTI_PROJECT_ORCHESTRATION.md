# Orquestacion multi-proyecto

Este documento define como el Agente debe coordinar MMNexus, Fabrica de Productos Digitales y su propio runtime.

## Objetivo

El Agente debe actuar como operador autonomo supervisado: detectar trabajo util, proponer cambios, ejecutar tareas de bajo riesgo y pedir autorizacion cuando haya impacto economico, publicacion externa, credenciales o cambios irreversibles.

## Proyectos

| Proyecto | Rol | Outputs esperados |
| --- | --- | --- |
| Agente | Orquestador, cola, permisos, Telegram, daemon 24/7 | planes, tareas, aprobaciones, reportes, ejecucion controlada |
| MMNexus | Hub comercial y de agentes para productos POD/contenido | analytics, generacion visual, QA, publicaciones, integraciones |
| Fabrica | Pipeline de productos digitales | ZIP maestro, ebooks, portadas, maquetas, cursos, videos, redes |

Nota operativa:
- `mmnexus-hub-review` se considera sandbox de pruebas. No forma parte del circuito principal de monitoreo diario salvo que Leo lo pida explicitamente.

## Flujo recomendado

1. Capturar idea o pedido desde CLI/Telegram.
2. Clasificar proyecto, riesgo y tipo de accion.
3. Crear tarea en cola con resultado esperado y criterios de aceptacion.
4. Ejecutar automaticamente solo si la politica lo permite.
5. Pedir aprobacion para acciones sensibles.
6. Guardar resultado, tests y siguiente recomendacion.

## Autonomia por defecto

| Accion | Decision |
| --- | --- |
| Leer archivos, resumir estado, crear planes | Autonomo |
| Crear documentos internos, backlog, checklists | Autonomo |
| Refactors pequenos con tests locales | Autonomo |
| Cambiar prompts o plantillas sin publicar | Autonomo |
| Modificar `.env`, tokens o secretos | Bloqueado |
| Publicar en redes, Shopify, Printify, Gumroad | Requiere aprobacion |
| Comprar servicios, activar paid APIs, crear recursos cloud | Requiere aprobacion |
| Borrar datos, resetear ramas, migraciones destructivas | Bloqueado salvo orden explicita |

## Skills internas sugeridas

| Skill | Uso |
| --- | --- |
| project-auditor | Revisa estado, tests, deuda y riesgos por repo |
| product-factory-planner | Convierte propuestas en entregables: ebook, portada, mockups, curso, video, redes |
| mmnexus-growth-operator | Propone mejoras de pipeline comercial, analytics y publishing |
| release-guardian | Valida antes de publicar o hacer deploy |
| token-optimizer | Reduce llamadas LLM usando cache, plantillas, resumen incremental y modelos baratos |

## Criterios de salida por proyecto

### Agente

- Cola persistente funcionando.
- Politica de autonomia documentada.
- Telegram con whitelist y aprobaciones.
- Daemon ejecutable localmente y portable a servidor.
- Logs suficientes para auditar decisiones.

### MMNexus

- `npm run lint` sin errores.
- `npm run type-check` sin errores.
- Telemetria resiliente sin depender 100% de Firestore.
- QA visual y publicacion con pasos aprobables.
- Integraciones externas aisladas y tipadas.

### Fabrica

- `npm run build` sin errores.
- Cada producto debe incluir entregables trabajables, no solo texto final.
- Para ebooks: indice, capitulos, portada, contraportada, mockup, descripcion comercial.
- Para cursos: temario, guion por modulo, slides o maqueta visual, assets promocionales.
- Para videos/redes: guion, storyboard, thumbnails, copies, calendario y checklist de QA.

## Optimizacion de tokens

- Usar routing deterministico antes de llamar modelos.
- Guardar resumen incremental de cada proyecto.
- Reutilizar briefs y plantillas versionadas.
- Separar tareas baratas deterministicamente: checklist, empaquetado, nombres de archivos, validaciones.
- Pedir al modelo solo decisiones creativas, analisis ambiguo o generacion de contenido.
- Usar aprobaciones humanas para evitar ciclos largos en acciones de alto costo.

## Proximo bloque de trabajo

1. Conectar tareas multi-proyecto a `work_queue.py`.
2. Crear comandos de reporte: estado de Agente, MMNexus y Fabrica.
3. Agregar perfiles de salida para ebooks, cursos, videos y apps en Fabrica.
4. Definir handoff: una propuesta de Fabrica puede crear tareas para MMNexus si requiere promocion o publicacion.
5. Preparar una alternativa a Oracle Cloud si la cuenta gratuita sigue bloqueada: maquina local always-on, Hetzner, Contabo, Render worker, Fly.io o VPS barato.
