from agent import Agent


def safe_print(message: str) -> None:
    print(message.encode("cp1252", errors="replace").decode("cp1252"))


def main():
    safe_print("Agent CLI v6 - operador multi-proyecto")
    safe_print("=" * 50)
    safe_print("Comandos:")
    safe_print("  /daily-brief              - Resumen operativo")
    safe_print("  /multi-status             - Estado de Agent, MMNexus y Fabrica")
    safe_print("  /queue                    - Ver cola activa")
    safe_print("  /approvals                - Ver aprobaciones pendientes")
    safe_print("  /daemon-status            - Estado del daemon")
    safe_print("  /project [agent|mmnexus|fabrica] - Cambiar proyecto")
    safe_print("  /help                     - Esta ayuda")
    safe_print("  salir                     - Terminar")
    safe_print("=" * 50)

    agent = Agent()

    while True:
        try:
            user_input = input(
                f"\n[{agent.current_project}] {agent.current_dir}\nTu: "
            ).strip()

            if not user_input:
                continue

            if user_input.lower() in ["salir", "exit", "quit"]:
                safe_print("Hasta luego.")
                break

            if user_input.lower() == "/help":
                safe_print(
                    """
Comandos disponibles:
  /daily-brief                 - Resumen operativo completo
  /multi-status                - Estado multi-proyecto
  /queue                       - Cola activa
  /queue-all                   - Historial de cola
  /approvals                   - Aprobaciones pendientes
  /daemon-status               - Estado del daemon
  /tg-diagnose                 - Diagnóstico de Telegram
  /project mmnexus             - Cambiar a MMNexus
  /project fabrica             - Cambiar a Fabrica
  /project agent               - Volver al repo del agente
                    """
                )
                continue

            response = agent.talk(user_input)
            safe_print(f"\nAgente:\n{response}")

        except KeyboardInterrupt:
            safe_print("\nInterrumpido")
            break
        except Exception as e:
            safe_print(f"Error: {e}")

if __name__ == "__main__":
    main()
