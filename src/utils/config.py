import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


def load_config() -> dict[str, Any]:
    config_path = ROOT_DIR / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Personal portfolio data (positions/funds) lives in a git-ignored
    # positions.yaml, not in config.yaml. Merge it into config["portfolio"]
    # so the load_config() interface is unchanged for all consumers.
    positions_path = Path(config_path).parent / "positions.yaml"
    if positions_path.exists():
        with open(positions_path, "r", encoding="utf-8") as f:
            positions_data = yaml.safe_load(f)
        config.setdefault("portfolio", {})
        config["portfolio"].update(positions_data["portfolio"])
    else:
        config.setdefault("portfolio", {})
        config["portfolio"].setdefault("positions", {})
        config["portfolio"].setdefault("funds", {})
        logger.warning(
            "positions.yaml bulunamadı — portföy verisi yok"
        )

    return config


def get_db_path() -> Path:
    env_path = os.getenv("DB_PATH", "data/bist_data.db")
    path = ROOT_DIR / env_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO")


def get_reports_dir() -> Path:
    config = load_config()
    output_dir = config.get("reporting", {}).get("output_dir", "reports")
    path = ROOT_DIR / output_dir
    path.mkdir(parents=True, exist_ok=True)
    return path
