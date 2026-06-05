import os
from pathlib import Path

from agent import Agent
from daemon_runner import DaemonRunner, env_digest_every, env_interval
from process_runtime import ProcessRuntimeTracker
from runtime_logging import setup_file_logger


def main():
    agent = Agent()
    state_dir = Path(agent.governance.state_dir)
    logger = setup_file_logger(
        "agent.daemon",
        state_dir / "logs" / "agent_daemon.log",
    )
    runtime_tracker = ProcessRuntimeTracker(
        state_file=state_dir / "agent_daemon_runtime.json",
        pid_file=state_dir / "agent_daemon.pid",
        process_name="agent_daemon",
    )
    runner = DaemonRunner(agent, agent.governance.state_dir, logger=logger, runtime_tracker=runtime_tracker)
    project = os.getenv("AGENT_DAEMON_PROJECT") or None
    runner.loop(
        interval_seconds=env_interval(),
        project=project,
        digest_every=env_digest_every(),
    )


if __name__ == "__main__":
    main()
