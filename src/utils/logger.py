import logging
import sys

from src.utils.config import ROOT_DIR, get_log_level


def setup_logger(name: str) -> logging.Logger:
    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    level = getattr(logging, get_log_level(), logging.INFO)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler(log_dir / "errors.log", encoding="utf-8")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger
