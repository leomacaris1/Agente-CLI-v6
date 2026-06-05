from pathlib import Path


def setup_store(agent, platform="gumroad"):
    print(f"? Configurando {platform}...")
    guides = {
        "gumroad": "# ? Gumroad (Gratis)\n\n1. gumroad.com ? Start Selling\n2. Products ? New Product\n3. Precio: $5-15\n4. Subir archivo digital\n5. Cover en Canva\n\nComisión: 10% + $0.30/venta",
        "instagram": "# ? Instagram Shop\n\n1. Cuenta Business\n2. Catálogo ? Facebook\n3. Link en bio (Linktree)\n4. 3 Reels/semana\n5. Stories diarios",
        "tiktok": "# ? TikTok Strategy\n\n1. Business Account\n2. Bio optimizada + link\n3. 3 videos/día (15-60s)\n4. Hooks 3s\n5. Trending sounds",
    }
    guide = guides.get(platform, "No disponible")
    project_dir = Path.home() / "Desktop" / "Digital-Business"
    with open(project_dir / f"{platform}_setup.md", "w", encoding="utf-8") as f:
        f.write(guide)
    agent._send_telegram(f"? Guía: {platform}")
    return f"? Guía: `{platform}_setup.md`\n\n{guide}"


def generate_content_batch(agent, quantity=5, platform="tiktok"):
    print(f"? Generando {quantity} contenidos...")
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
        res = agent.client.chat.completions.create(
            model=agent.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
        )
        content = res.choices[0].message.content
        project_dir = Path.home() / "Desktop" / "Digital-Business"
        content_file = project_dir / "social-media" / f"content_{platform}.md"
        with open(content_file, "w", encoding="utf-8") as f:
            f.write(f"# ? Content {platform}\n\n{content}")
        agent._send_telegram(f"? {quantity} contenidos generados")
        return f"? Contenido:\n\n{content[:1000]}..."
    except Exception as e:
        return f"? Error: {e}"


def track_metrics(agent):
    print("? Actualizando dashboard...")
    project_dir = Path.home() / "Desktop" / "Digital-Business"
    tasks_file = project_dir / "daily_tasks.json"
    completed = 0
    if tasks_file.exists():
        with open(tasks_file, "r", encoding="utf-8") as f:
            try:
                data = __import__("json").load(f)
                completed = len(data.get("completed", []))
            except Exception:
                pass

    gumroad_stats = ""
    if agent.gumroad.token:
        try:
            stats = agent.gumroad.get_stats()
            if stats.get("success"):
                gumroad_stats = (
                    f"\n\n## ? Ventas Gumroad\n"
                    f"- Productos activos: {stats['active_products']}\n"
                    f"- Ventas totales: {stats['total_sales']}\n"
                    f"- Ingresos: {stats['total_revenue']}"
                )
        except Exception:
            gumroad_stats = "\n\n## ? Ventas Gumroad\n?? Error al conectar"

    dashboard = f"""# ? Dashboard

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
{gumroad_stats}

*{agent.CURRENT_DATE if hasattr(agent, 'CURRENT_DATE') else ''}*"""

    with open(project_dir / "dashboard.md", "w", encoding="utf-8") as f:
        f.write(dashboard)
    return f"? Dashboard actualizado\n\n{dashboard}"


def generate_product_content(agent, product_name: str):
    print(f"? Generando contenido para: {product_name}")
    prompt = f"""Sos un experto creador de productos digitales.
Tu tarea es crear el contenido COMPLETO del siguiente producto:
NOMBRE: {product_name}

REQUISITOS:
1. El contenido debe ser extenso, útil y de alta calidad.
2. Estructura: Introducción, Pasos detallados, Ejemplos prácticos, Conclusión.
3. Formato: Markdown claro.
4. NO incluyas títulos de producto ni precios, solo el contenido que el usuario leerá.
"""
    try:
        res = agent.client.chat.completions.create(
            model=agent.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        content = res.choices[0].message.content
        safe_name = product_name.replace(" ", "_").lower()
        file_path = Path.home() / "Desktop" / "Digital-Business" / "products" / f"{safe_name}.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {product_name}\n\n{content}")
        agent._send_telegram(f"? Producto creado:\n? {file_path.name}")
        return f"? Contenido generado y guardado en `products/{safe_name}.md`. Listo para publicar."
    except Exception as e:
        return f"? Error generando contenido: {e}"


def publish_to_gumroad(agent, name="", description="", price_usd=5.0, content_file_path=""):
    if not agent.gumroad.token:
        return "?? Configurá GUMROAD_TOKEN en tu archivo .env"

    products_dir = Path.home() / "Desktop" / "Digital-Business" / "products"

    if content_file_path:
        product_file = Path(content_file_path)
    else:
        if not products_dir.exists():
            return "? No hay carpeta de productos."
        files = list(products_dir.glob("*.md"))
        if not files:
            return "? No hay productos generados en la carpeta 'products'. Ejecutá 'Generar contenido...' primero."
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        product_file = files[0]

    if not product_file.exists():
        return f"? Archivo no encontrado: {product_file}"

    content_to_upload = product_file.read_text(encoding="utf-8")
    product_name = product_file.stem.replace("_", " ").title()
    prompt_desc = (
        "Crea una descripción de venta persuasiva y corta (max 100 palabras) "
        f"para este producto:\n{content_to_upload[:1000]}"
    )
    try:
        res = agent.client.chat.completions.create(
            model=agent.model,
            messages=[{"role": "user", "content": prompt_desc}],
            max_tokens=300,
        )
        description = res.choices[0].message.content
    except Exception:
        description = f"Producto digital: {product_name}"

    print(f"? Publicando en Gumroad: {product_name}")
    result = agent.gumroad.create_product(
        product_name,
        description,
        price_usd,
        content_text=content_to_upload,
    )

    if result.get("success"):
        agent._send_telegram(f"? ¡PUBLICADO!\n? {result['name']}\n? ${price_usd}\n? {result['url']}")
        return (
            f"? Producto publicado!\n\n"
            f"? **{result['name']}**\n"
            f"? Precio: {result['price']}\n"
            f"? Link: {result['url']}\n\n"
            "*El contenido ha sido subido automáticamente*"
        )
    return f"? Error al publicar: {result.get('error', 'Error desconocido')}"


def check_gumroad_sales(agent):
    if not agent.gumroad.token:
        return "?? Configurá GUMROAD_TOKEN en .env"

    print("? Verificando ventas en Gumroad...")
    stats = agent.gumroad.get_stats()
    if not stats.get("success"):
        return f"? Error: {stats.get('error')}"

    report = f"""# ? Reporte de Ventas Gumroad

## Resumen
- **Productos activos:** {stats['active_products']}
- **Ventas totales:** {stats['total_sales']}
- **Ingresos totales:** {stats['total_revenue']}

## Últimas ventas
"""
    for sale in stats.get("recent_sales", []):
        report += f"- {sale.get('product_name', 'N/A')}: ${sale.get('price', 0)} ({sale.get('created_at', 'N/A')[:10]})\n"

    if not stats.get("recent_sales"):
        report += "_Sin ventas registradas aún_"

    agent._send_telegram(f"? Ventas Gumroad:\nTotal: {stats['total_revenue']}\nVentas: {stats['total_sales']}")
    return report


def list_gumroad_products(agent):
    if not agent.gumroad.token:
        return "?? Configurá GUMROAD_TOKEN en .env"

    products = agent.gumroad.list_products()
    if not products:
        return "? No hay productos en Gumroad"

    report = "# ? Productos en Gumroad\n\n"
    for product in products:
        status = "? Activo" if product.get("published") else "?? Borrador"
        report += (
            f"- **{product['name']}** ({status})\n"
            f"  ? ${product['price'] / 100:.2f} | "
            f"? gumroad.com/l/{product.get('custom_permalink', product['id'])}\n\n"
        )
    return report
