import logging
import os
from pathlib import Path


def setup_file_logger(name: str, log_file: Path) -> logging.Logger:
    logger = logging.getLogger(name)
    if getattr(logger, "_agent_cli_configured", False):
        return logger

    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
    except PermissionError:
        fallback_file = log_file.with_name(f"{log_file.stem}.{os.getpid()}{log_file.suffix}")
        file_handler = logging.FileHandler(fallback_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger._agent_cli_configured = True
    return logger
