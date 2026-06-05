#!/usr/bin/env python3
"""Fail fast if known secrets leak into logs or process command lines."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / ".agent_state" / "logs"
ENV_FILE = ROOT / ".env"
MAX_MATCHES_PER_FILE = 10
PROCESS_SCOPE_MARKERS = (
    "agent_daemon.py",
    "telegram_poll.py",
    "telegram_operator.py",
    str(ROOT).lower(),
    "c:\\users\\leoma\\mmnexus-hub",
    "c:\\users\\leoma\\onedrive\\desktop\\apps\\fabrica-productos-digitales",
)

GENERIC_PATTERNS = {
    "telegram_bot_token": re.compile(r"/bot\d{6,}:[A-Za-z0-9_-]{20,}"),
    "google_api_key": re.compile(r"X-Goog-Api-Key:\s*[A-Za-z0-9._-]+"),
    "supabase_pat": re.compile(r"sbp_[A-Za-z0-9]+"),
}

ALLOWLIST_SNIPPETS = {
    "<redacted-telegram-token>",
    "your_telegram_bot_token",
    "TELEGRAM_BOT_TOKEN=***",
}


def load_env_secrets(path: Path) -> dict[str, str]:
    secrets: dict[str, str] = {}
    if not path.exists():
        return secrets

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"TELEGRAM_BOT_TOKEN", "OPENROUTER_API_KEY", "API_KEY", "GUMROAD_TOKEN"}:
            value = value.strip()
            if value and not value.startswith("your_"):
                secrets[key] = value
    return secrets


def sanitize_preview(text: str, secrets: Iterable[str]) -> str:
    preview = text
    for secret in secrets:
        if secret:
            preview = preview.replace(secret, "<redacted>")
    return preview[:220]


def scan_text(label: str, text: str, env_secrets: dict[str, str]) -> list[str]:
    findings: list[str] = []
    secrets = tuple(env_secrets.values())
    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        if any(marker in line for marker in ALLOWLIST_SNIPPETS):
            continue

        for key, secret in env_secrets.items():
            if secret and secret in line:
                findings.append(
                    f"{label}:{lineno}: contains {key} -> {sanitize_preview(line, secrets)}"
                )

        for name, pattern in GENERIC_PATTERNS.items():
            if pattern.search(line):
                findings.append(
                    f"{label}:{lineno}: matches {name} -> {sanitize_preview(line, secrets)}"
                )

        if len(findings) >= MAX_MATCHES_PER_FILE:
            findings.append(f"{label}: additional matches omitted")
            break

    return findings


def scan_logs(env_secrets: dict[str, str]) -> list[str]:
    findings: list[str] = []
    if not LOG_DIR.exists():
        return findings

    for log_file in sorted(LOG_DIR.glob("*.log")):
        text = log_file.read_text(encoding="utf-8", errors="ignore")
        findings.extend(scan_text(str(log_file.relative_to(ROOT)), text, env_secrets))
    return findings


def get_process_command_lines() -> list[dict[str, str]]:
    command = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(result.stderr.strip() or "Unable to inspect processes.")

    data = json.loads(result.stdout)
    if isinstance(data, dict):
        return [data]
    return data


def scan_processes(env_secrets: dict[str, str]) -> list[str]:
    findings: list[str] = []
    processes = get_process_command_lines()
    secrets = tuple(env_secrets.values())

    for process in processes:
        command_line = process.get("CommandLine") or ""
        if not command_line:
            continue
        lowered = command_line.lower()
        if not any(marker in lowered for marker in PROCESS_SCOPE_MARKERS):
            continue
        if any(marker in command_line for marker in ALLOWLIST_SNIPPETS):
            continue

        label = f"process:{process.get('ProcessId')}:{process.get('Name')}"
        findings.extend(scan_text(label, command_line, env_secrets))
        if len(findings) >= 25:
            findings.append("process scan: additional matches omitted")
            break

    return findings


def main() -> int:
    env_secrets = load_env_secrets(ENV_FILE)
    if not env_secrets:
        print("No secrets loaded from .env; nothing to scan.")
        return 0

    findings: list[str] = []
    findings.extend(scan_logs(env_secrets))

    try:
        findings.extend(scan_processes(env_secrets))
    except RuntimeError as exc:
        print(f"Secret exposure check could not inspect processes: {exc}")
        return 2

    if findings:
        print("Secret exposure check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Secret exposure check passed: no raw secrets found in logs or process command lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
