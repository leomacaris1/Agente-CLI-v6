from __future__ import annotations

from agent import Agent


def test_agent_initializes_projects() -> None:
    agent = Agent()

    assert agent.current_project == "agent"
    assert set(agent.projects) == {"agent", "mmnexus", "fabrica"}
    assert agent.work_queue is not None


def test_agents_command_returns_listing() -> None:
    agent = Agent()

    result = agent.talk("/agents")

    assert isinstance(result, str)
    assert result.strip()
