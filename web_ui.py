import gradio as gr
from agent import Agent

agent = Agent()

def responder(mensaje):
    try:
        print(f"📩 Recibido: {mensaje}")
        respuesta = agent.talk(mensaje)
        return respuesta
    except Exception as e:
        return f"❌ Error: {str(e)}"

with gr.Blocks(title="Agente CLI v5") as demo:
    gr.Markdown("# 🦅 Agente CLI v5")
    gr.Markdown("Sistema multiagente + Negocio digital")
    
    chatbot = gr.Chatbot(height=400)
    msg = gr.Textbox(label="Mensaje", placeholder="/agents, /init-business...")
    clear = gr.Button("Limpiar")
    
    def user(user_message, history):
        if history is None:
            history = []
        return "", history + [[user_message, None]]
    
    def bot(history):
        if not history or not history[-1][0]:
            return history
        user_message = history[-1][0]
        bot_response = responder(user_message)
        history[-1][1] = bot_response
        return history
    
    msg.submit(user, [msg, chatbot], [msg, chatbot]).then(
        bot, chatbot, chatbot
    )
    
    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(server_port=7862)