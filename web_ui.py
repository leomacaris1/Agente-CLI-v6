import gradio as gr

from agent import Agent


agent = Agent()


QUICK_COMMANDS = [
    ("Daily brief", "/daily-brief"),
    ("Multi status", "/multi-status"),
    ("Cola activa", "/queue"),
    ("Historial cola", "/queue-all"),
    ("Presupuesto", "/budget"),
    ("Telegram", "/tg-diagnose"),
    ("Aprobaciones", "/approvals"),
    ("Daemon", "/daemon-status"),
    ("Sembrar tareas", "/seed-multi-project"),
]


def responder(mensaje, historial):
    try:
        if not mensaje:
            return historial or "", ""

        print(f"Recibido: {mensaje}")
        historial = historial or ""
        respuesta = agent.talk(mensaje)
        print("Respondido")

        nuevo_historial = (
            historial
            + f"\n\nTu: {mensaje}\n\n"
            + f"Agente:\n{respuesta}\n"
            + "=" * 60
        )
        return nuevo_historial, ""
    except Exception as e:
        print(f"Error: {e}")
        historial = historial or ""
        historial += f"\n\nError: {str(e)}"
        return historial, ""


def ejecutar_comando(comando, historial):
    return responder(comando, historial)


def estado_inicial():
    telegram = "configurado" if agent.telegram_operator.is_configured() else "sin configurar"
    return (
        "Agente CLI v6 - operador multi-proyecto\n\n"
        f"Proyecto actual: {agent.current_project}\n"
        f"Telegram: {telegram}\n"
        "Usa los botones para operar Agente, MMNexus y Fabrica sin recordar comandos."
    )


css = """
.leo-header {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px 16px;
  background: #f8fafc;
}
.leo-hint {
  color: #475569;
  font-size: 13px;
}
textarea {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
"""


with gr.Blocks(title="Agente Leo - Operador", css=css) as demo:
    gr.Markdown(
        """
<div class="leo-header">
  <h1>Agente Leo</h1>
  <p class="leo-hint">Panel local para orquestar Agente, MMNexus y Fabrica.</p>
</div>
"""
    )

    gr.Markdown(estado_inicial())

    historial = gr.Textbox(
        label="Conversacion y reportes",
        placeholder="La conversacion aparecera aqui...",
        lines=20,
        max_lines=60,
        interactive=False,
    )

    with gr.Row():
        msg_input = gr.Textbox(
            label="Tu mensaje",
            placeholder="Ej: /daily-brief, /queue, /propose-task revisar analytics de MMNexus",
            scale=8,
            autofocus=True,
        )
        btn_send = gr.Button("Enviar", variant="primary", scale=1)

    gr.Markdown("### Operacion rapida")
    with gr.Row():
        for label, command in QUICK_COMMANDS[:3]:
            gr.Button(label).click(
                fn=lambda h, c=command: ejecutar_comando(c, h),
                inputs=[historial],
                outputs=[historial, msg_input],
            )

    with gr.Row():
        for label, command in QUICK_COMMANDS[3:6]:
            gr.Button(label).click(
                fn=lambda h, c=command: ejecutar_comando(c, h),
                inputs=[historial],
                outputs=[historial, msg_input],
            )

    with gr.Row():
        for label, command in QUICK_COMMANDS[6:]:
            gr.Button(label).click(
                fn=lambda h, c=command: ejecutar_comando(c, h),
                inputs=[historial],
                outputs=[historial, msg_input],
            )

    with gr.Accordion("Comandos utiles", open=False):
        gr.Examples(
            examples=[
                "/daily-brief",
                "/multi-status",
                "/queue",
                "/queue-all",
                "/budget",
                "/budget-check 5 ads prueba",
                "/tg-diagnose",
                "/daemon-status",
                "/propose-task MMNexus: diagnosticar analytics vacio",
                "/propose-task Fabrica: generar paquete trabajable para ebook",
            ],
            inputs=msg_input,
            label="Selecciona un comando",
        )

    with gr.Row():
        btn_clear = gr.Button("Limpiar conversacion")

    msg_input.submit(
        fn=responder,
        inputs=[msg_input, historial],
        outputs=[historial, msg_input],
    )

    btn_send.click(
        fn=responder,
        inputs=[msg_input, historial],
        outputs=[historial, msg_input],
    )

    btn_clear.click(
        fn=lambda: ("", ""),
        inputs=None,
        outputs=[historial, msg_input],
        queue=False,
    )


if __name__ == "__main__":
    demo.launch(server_port=7862)
