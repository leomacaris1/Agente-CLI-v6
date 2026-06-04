#!/usr/bin/env python3
"""Manual smoke script for Agent CLI v6."""

from __future__ import annotations

from typing import Any


def safe_print(message: str) -> None:
    print(message.encode("cp1252", errors="replace").decode("cp1252"))


def main() -> int:
    safe_print("[smoke] Testing Agent CLI v6...")

    safe_print("1. Importing modules...")
    try:
      from agent import Agent, NATIVE_TOOLS
      from memory import MemoryBank
      from subagents import SubAgentRegistry
    except Exception as exc:
      safe_print(f"[fail] Import error: {exc}")
      return 1
    safe_print("[ok] Modules imported")

    safe_print("2. Checking native tools...")
    safe_print(f"   Total tools: {len(NATIVE_TOOLS)}")
    for tool in NATIVE_TOOLS:
      safe_print(
        f"   - {tool['function']['name']}: {tool['function']['description'][:50]}..."
      )

    safe_print("3. Creating agent instance...")
    agent: Any | None = None
    try:
      agent = Agent()
      safe_print(f"[ok] Agent created: {agent.model}")
      safe_print(f"   Directory: {agent.current_dir}")
      safe_print(f"   Registered subagents: {len(agent.subagents.agents)}")
      safe_print(f"   Memory backend: {type(MemoryBank()).__name__}")
      safe_print(f"   Registry backend: {SubAgentRegistry.__name__}")
    except Exception as exc:
      safe_print(f"[warn] Agent created with warnings: {exc}")

    safe_print("4. Listing subagents...")
    if agent is not None:
      try:
        agents_list = agent.subagents.list_agents()
        safe_print(agents_list[:500] + "...")
      except Exception as exc:
        safe_print(f"[fail] Error listing agents: {exc}")

    safe_print("5. Running /agents...")
    if agent is not None:
      try:
        result = agent.talk("/agents")
        safe_print(result[:300] + "...")
      except Exception as exc:
        safe_print(f"[fail] Error running /agents: {exc}")

    safe_print("[ok] Smoke script finished")
    safe_print("Next: add API_KEY to .env and run `python web_ui.py` for interactive usage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
