import logging
import os
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from dotenv import load_dotenv


load_dotenv(Path.cwd() / ".env")


class TelegramOperator:
    def __init__(self, token: str = "", chat_id: str = ""):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = str(chat_id or os.getenv("TELEGRAM_CHAT_ID", ""))
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self.logger = logging.getLogger("agent.telegram")

    def _mask_token(self, value: str) -> str:
        if not value:
            return value
        return value.replace(self.token, "<redacted-telegram-token>")

    def _sanitize_error(self, error: object) -> str:
        text = self._mask_token(str(error))
        if "api.telegram.org" not in text:
            return text

        parts = urlsplit(text)
        if not parts.scheme or not parts.netloc:
            return text

        query = []
        for key, value in parse_qsl(parts.query, keep_blank_values=True):
            if key.lower() in {"token", "authorization"}:
                query.append((key, "<redacted>"))
            else:
                query.append((key, value))

        sanitized_path = parts.path.replace(self.token, "<redacted-telegram-token>")
        sanitized_query = urlencode(query)
        return urlunsplit((parts.scheme, parts.netloc, sanitized_path, sanitized_query, parts.fragment))

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_message(self, text: str, chat_id: Optional[str] = None) -> str:
        if not self.is_configured():
            self.logger.warning("Intento de envio con Telegram no configurado.")
            return "Telegram no configurado."
        target_chat = str(chat_id or self.chat_id)
        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": target_chat,
                    "text": text[:3900],
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            if response.status_code == 200:
                self.logger.info("Mensaje enviado a Telegram | chat_id=%s", target_chat)
                return "Enviado"
            self.logger.warning("Error Telegram %s: %s", response.status_code, response.text[:400])
            return f"Error Telegram {response.status_code}: {response.text}"
        except Exception as e:
            self.logger.warning("Excepcion enviando mensaje a Telegram: %s", self._sanitize_error(e))
            return f"Error Telegram: {self._sanitize_error(e)}"

    def get_updates(self, offset: Optional[int] = None, timeout: int = 20) -> Dict:
        if not self.is_configured():
            self.logger.warning("Intento de polling con Telegram no configurado.")
            return {"ok": False, "error": "Telegram no configurado"}
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        try:
            response = requests.get(f"{self.base_url}/getUpdates", params=params, timeout=timeout + 5)
            self.logger.info("Polling Telegram OK | offset=%s | timeout=%s", offset, timeout)
            return response.json()
        except Exception as e:
            sanitized_error = self._sanitize_error(e)
            self.logger.warning("Excepcion haciendo polling a Telegram: %s", sanitized_error)
            return {"ok": False, "error": sanitized_error}

    def diagnose(self) -> str:
        lines = ["Diagnostico Telegram"]
        lines.append(f"- Token configurado: {'si' if self.token else 'no'}")
        lines.append(f"- Chat ID configurado: {'si' if self.chat_id else 'no'}")

        if not self.token:
            lines.append("- Resultado: falta TELEGRAM_BOT_TOKEN.")
            return "\n".join(lines)

        try:
            me = requests.get(f"{self.base_url}/getMe", timeout=10).json()
            if not me.get("ok"):
                lines.append(f"- getMe: fallo ({me.get('description') or me})")
                return "\n".join(lines)
            bot = me.get("result", {})
            lines.append(f"- Bot: @{bot.get('username', 'sin_username')} ({bot.get('first_name', 'sin_nombre')})")
        except Exception as e:
            lines.append(f"- getMe: error {e}")
            return "\n".join(lines)

        if not self.chat_id:
            lines.append("- Resultado: falta TELEGRAM_CHAT_ID.")
            return "\n".join(lines)

        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": "Diagnostico Telegram: conexion OK"},
                timeout=10,
            )
            if response.status_code == 200:
                lines.append("- Envio de prueba: OK")
                lines.append("- Resultado: Telegram esta listo.")
                return "\n".join(lines)
            lines.append(f"- Envio de prueba: fallo {response.status_code} ({response.text})")
        except Exception as e:
            lines.append(f"- Envio de prueba: error {e}")

        updates = self.get_updates(timeout=3)
        if updates.get("ok"):
            commands = [self.extract_command(update) for update in updates.get("result", [])]
            commands = [command for command in commands if command]
            if commands:
                lines.append("- Ultimos chats detectados por getUpdates:")
                for command in commands[-5:]:
                    lines.append(
                        f"  chat_id={command.get('chat_id')} "
                        f"authorized={command.get('authorized')} text={command.get('text')}"
                    )
            else:
                lines.append("- getUpdates: sin mensajes recientes.")
        else:
            lines.append(f"- getUpdates: fallo ({updates.get('description') or updates.get('error')})")

        lines.append("- Siguiente paso: abre el bot en Telegram, envia /start, luego ejecuta /tg-diagnose.")
        lines.append("- Si getUpdates muestra otro chat_id, copia ese valor a TELEGRAM_CHAT_ID.")
        return "\n".join(lines)

    def extract_command(self, update: Dict) -> Optional[Dict]:
        message = update.get("message") or update.get("edited_message") or {}
        text = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if not text:
            return None
        return {
            "update_id": update.get("update_id"),
            "chat_id": chat_id,
            "text": text,
            "authorized": self.is_authorized(chat_id),
        }

    def is_authorized(self, chat_id: str) -> bool:
        return bool(self.chat_id and str(chat_id) == self.chat_id)

    def format_digest(self, queue_summary: str, approvals_summary: str, projects_summary: str) -> str:
        return (
            "Resumen del agente\n\n"
            "Proyectos\n"
            f"{projects_summary}\n\n"
            "Cola\n"
            f"{queue_summary}\n\n"
            "Aprobaciones\n"
            f"{approvals_summary}"
        )

    def format_help(self) -> str:
        return (
            "Comandos disponibles\n"
            "/tg-diagnose - diagnosticar token/chat\n"
            "/tg-status - resumen operativo\n"
            "/daily-brief - tablero operativo completo\n"
            "/budget - politica economica\n"
            "/queue - ver tareas activas\n"
            "/queue-all - ver historial\n"
            "/queue-next - proxima tarea\n"
            "/queue-run-next - ejecutar proxima tarea segura\n"
            "/approvals - aprobaciones pendientes\n"
            "/approve <id> - aprobar\n"
            "/reject <id> - rechazar\n"
            "/propose-task <tarea> - proponer tarea"
        )
