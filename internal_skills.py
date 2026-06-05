from datetime import datetime
from pathlib import Path


class InternalSkillRegistry:
    def run(self, action_type, worker, title, project, project_path, output_root):
        output_root = Path(output_root)
        output_root.mkdir(parents=True, exist_ok=True)

        if project == "fabrica" and action_type == "content_generation":
            return self._run_product_factory(title, project, output_root)
        if action_type == "analysis":
            return self._run_project_audit(title, project, project_path, output_root)
        if action_type == "draft":
            return self._run_operational_plan(title, project, output_root)
        if action_type == "read":
            return self._run_read_snapshot(title, project, project_path, output_root)

        return self._run_operational_plan(title, project, output_root)

    def _run_product_factory(self, title, project, output_root):
        product_type = self._detect_product_type(title)
        package_dir = output_root / self._slug(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{title}")
        package_dir.mkdir(parents=True, exist_ok=True)

        artifacts = {
            "manifest.md": self._product_manifest(title, product_type),
            "cover_prompt.md": self._cover_prompt(title, product_type),
            "mockup.md": self._mockup_brief(title, product_type),
            "launch_kit.md": self._launch_kit(title, product_type),
            "qa_checklist.md": self._qa_checklist(product_type),
        }

        paths = []
        for filename, content in artifacts.items():
            path = package_dir / filename
            path.write_text(content, encoding="utf-8")
            paths.append(path)

        return self._summary("Producto digital preparado", paths)

    def _run_project_audit(self, title, project, project_path, output_root):
        project_path = Path(project_path)
        package_dir = output_root / self._slug(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{title}")
        package_dir.mkdir(parents=True, exist_ok=True)
        files = self._safe_list(project_path)
        signals = self._project_signals(project_path)
        content = (
            f"# Auditoria de proyecto\n\n"
            f"Proyecto: {project}\n"
            f"Tarea: {title}\n"
            f"Ruta: {project_path}\n\n"
            "## Senales detectadas\n"
            + "\n".join([f"- {signal}" for signal in signals])
            + "\n\n## Archivos principales\n"
            + "\n".join([f"- {item}" for item in files[:40]])
            + "\n\n## Siguiente paso recomendado\n"
            "- Convertir hallazgos en tareas pequenas y encolarlas con `/propose-task`.\n"
            "- Pedir aprobacion antes de instalar, desplegar o ejecutar comandos.\n"
        )
        path = package_dir / "audit.md"
        path.write_text(content, encoding="utf-8")
        return self._summary("Auditoria generada", [path])

    def _run_operational_plan(self, title, project, output_root):
        package_dir = output_root / self._slug(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{title}")
        package_dir.mkdir(parents=True, exist_ok=True)
        content = (
            f"# Plan operativo\n\n"
            f"Proyecto: {project}\n"
            f"Tarea: {title}\n\n"
            "## Objetivo\n"
            "Definir una ejecucion reversible, observable y facil de aprobar.\n\n"
            "## Pasos\n"
            "1. Confirmar alcance y resultado esperado.\n"
            "2. Preparar artefactos en borrador.\n"
            "3. Revisar riesgos y dependencias.\n"
            "4. Encolar acciones sensibles como aprobaciones.\n"
            "5. Ejecutar solo cambios pequenos y verificables.\n\n"
            "## Criterios de listo\n"
            "- Hay salida revisable.\n"
            "- No se hicieron acciones externas sin aprobacion.\n"
            "- El siguiente paso esta expresado como tarea concreta.\n"
        )
        path = package_dir / "plan.md"
        path.write_text(content, encoding="utf-8")
        return self._summary("Plan operativo generado", [path])

    def _run_read_snapshot(self, title, project, project_path, output_root):
        project_path = Path(project_path)
        package_dir = output_root / self._slug(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{title}")
        package_dir.mkdir(parents=True, exist_ok=True)
        files = self._safe_list(project_path)
        content = (
            f"# Snapshot de lectura\n\n"
            f"Proyecto: {project}\n"
            f"Tarea: {title}\n"
            f"Ruta: {project_path}\n\n"
            "## Estructura visible\n"
            + "\n".join([f"- {item}" for item in files[:80]])
            + "\n"
        )
        path = package_dir / "snapshot.md"
        path.write_text(content, encoding="utf-8")
        return self._summary("Snapshot generado", [path])

    def _detect_product_type(self, title):
        text = title.lower()
        if "curso" in text:
            return "curso"
        if "video" in text or "guion" in text:
            return "video"
        if "app" in text or "saas" in text:
            return "app"
        if "plantilla" in text or "template" in text:
            return "plantilla"
        return "ebook"

    def _product_manifest(self, title, product_type):
        return (
            f"# Product Manifest\n\n"
            f"Titulo de trabajo: {title}\n"
            f"Tipo: {product_type}\n"
            "Estado: borrador trabajable\n\n"
            "## Promesa\n"
            "Ayudar al usuario objetivo a lograr un resultado especifico con un recurso digital claro y accionable.\n\n"
            "## Entregables minimos\n"
            "- Contenido principal.\n"
            "- Portada o thumbnail.\n"
            "- Mockup/preview.\n"
            "- Copy de venta.\n"
            "- Kit de lanzamiento para redes.\n\n"
            "## Requiere aprobacion antes de\n"
            "- Publicar.\n"
            "- Cambiar precio.\n"
            "- Enviar contenido comercial.\n"
        )

    def _cover_prompt(self, title, product_type):
        return (
            f"# Cover Prompt\n\n"
            f"Producto: {title}\n"
            f"Formato: {product_type}\n\n"
            "Crear una portada clara, comercial y legible en mobile. Debe comunicar el resultado principal, "
            "usar contraste alto, jerarquia tipografica profesional y evitar saturacion visual. "
            "Incluir espacio para titulo, subtitulo corto y marca si aplica.\n\n"
            "## Variantes\n"
            "- Portada principal.\n"
            "- Thumbnail cuadrado para redes.\n"
            "- Mockup de producto digital.\n"
        )

    def _mockup_brief(self, title, product_type):
        return (
            f"# Mockup Brief\n\n"
            f"Producto: {title}\n"
            f"Tipo: {product_type}\n\n"
            "## Objetivo\n"
            "Crear una maqueta que permita vender o revisar el producto antes de publicarlo.\n\n"
            "## Pantallas o vistas esperadas\n"
            "- Preview del producto.\n"
            "- Vista de contenido interno.\n"
            "- Imagen promocional para landing o Gumroad.\n"
        )

    def _launch_kit(self, title, product_type):
        return (
            f"# Launch Kit\n\n"
            f"Producto: {title}\n"
            f"Tipo: {product_type}\n\n"
            "## TikTok / Reels\n"
            "1. Hook: El problema que este producto resuelve en una frase.\n"
            "2. Desarrollo: Mostrar antes/despues o proceso.\n"
            "3. CTA: Descargar o ver el producto.\n\n"
            "## Instagram carrusel\n"
            "- Slide 1: Resultado deseado.\n"
            "- Slide 2: Dolor actual.\n"
            "- Slide 3: Mini solucion.\n"
            "- Slide 4: Que incluye el producto.\n"
            "- Slide 5: CTA.\n\n"
            "## Gumroad copy\n"
            "- Titulo claro.\n"
            "- Beneficio principal.\n"
            "- Lista de entregables.\n"
            "- Para quien es.\n"
            "- Garantia o nota de uso.\n"
        )

    def _qa_checklist(self, product_type):
        return (
            f"# QA Checklist\n\n"
            f"Tipo: {product_type}\n\n"
            "- [ ] El producto tiene una promesa concreta.\n"
            "- [ ] La portada es legible en mobile.\n"
            "- [ ] Hay mockup o preview.\n"
            "- [ ] El copy de venta no promete resultados falsos.\n"
            "- [ ] El launch kit esta alineado con el producto.\n"
            "- [ ] Publicacion y precio esperan aprobacion.\n"
        )

    def _safe_list(self, path):
        try:
            if not path.exists():
                return [f"Ruta no existe: {path}"]
            return [item.name + ("/" if item.is_dir() else "") for item in path.iterdir() if not item.name.startswith(".")]
        except Exception as e:
            return [f"No se pudo listar: {e}"]

    def _project_signals(self, path):
        signals = []
        checks = {
            "package.json": "Proyecto Node/JavaScript detectado.",
            "requirements.txt": "Proyecto Python con requirements detectado.",
            "pyproject.toml": "Proyecto Python moderno detectado.",
            "README.md": "README presente.",
            "src": "Carpeta src presente.",
            "tests": "Carpeta tests presente.",
        }
        for filename, message in checks.items():
            if (path / filename).exists():
                signals.append(message)
        return signals or ["No se detectaron senales estandar en la raiz."]

    def _summary(self, title, paths):
        rendered = "\n".join([f"- {path}" for path in paths])
        return f"{title}:\n{rendered}"

    def _slug(self, text):
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in text)
        return "_".join(part for part in safe.split("_") if part)[:90] or "task"
