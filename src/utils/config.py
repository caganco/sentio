import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent.parent


def load_config() -> dict[str, Any]:
    config_path = ROOT_DIR / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
