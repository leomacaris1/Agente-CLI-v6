import time
from pathlib import Path

from agent import Agent
from process_runtime import ProcessRuntimeTracker, utc_now
from runtime_logging import setup_file_logger


HEARTBEAT_INTERVAL_SECONDS = 300


def main():
    agent = Agent()
    state_dir = Path(agent.governance.state_dir)
    logger = setup_file_logger(
        "agent.telegram_poll",
        state_dir / "logs" / "telegram_poll.log",
    )
    runtime_tracker = ProcessRuntimeTracker(
        state_file=state_dir / "telegram_poll_state.json",
        pid_file=state_dir / "telegram_poll.pid",
        process_name="telegram_poll",
    )
    operator = agent.telegram_operator
    if not operator.is_configured():
        logger.warning("Telegram no configurado. Defini TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.")
        runtime_tracker.start(configured=False)
        runtime_tracker.record_error(
            "Telegram no configurado",
            configured=False,
        )
        return

    logger.info("Telegram polling iniciado.")
    runtime_tracker.start(
        configured=True,
        status="running",
    )
    offset = None
    last_heartbeat_at = time.monotonic()
    while True:
        updates = operator.get_updates(offset=offset, timeout=20)
        if not updates.get("ok"):
            error = updates.get("error")
            logger.warning("Error polling Telegram: %s", error)
            runtime_tracker.record_error(str(error), configured=True)
            time.sleep(5)
            continue

        now = utc_now()
        results = updates.get("result", [])
        runtime_tracker.heartbeat(
            configured=True,
            last_successful_poll_at=now,
            last_error=None,
            status="running",
            last_update_count=len(results),
        )
        if time.monotonic() - last_heartbeat_at >= HEARTBEAT_INTERVAL_SECONDS:
            logger.info("Heartbeat polling Telegram | updates=%s", len(results))
            last_heartbeat_at = time.monotonic()

        for update in results:
            offset = update.get("update_id", 0) + 1
            command = operator.extract_command(update)
            if not command:
                continue
            runtime_tracker.heartbeat(
                configured=True,
                last_command_at=utc_now(),
                last_command_text=command["text"],
                last_command_chat_id=command["chat_id"],
            )
            logger.info("Comando recibido | chat_id=%s | text=%s", command["chat_id"], command["text"])
            response = agent.handle_telegram_command(command["text"], command["chat_id"])
            send_result = operator.send_message(response, chat_id=command["chat_id"])
            runtime_tracker.heartbeat(
                configured=True,
                last_response_at=utc_now(),
                last_send_result=str(send_result),
            )
            logger.info("Respuesta enviada | resultado=%s", send_result)


if __name__ == "__main__":
    main()
