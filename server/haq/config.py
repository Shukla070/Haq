"""Settings, read from the environment. server/.env is loaded if present; real
environment variables win over it."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent


def load_env(path: Path = SERVER_DIR / ".env") -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def model() -> str:
    return os.environ.get("MODEL_API_MODEL") or "muse-spark-1.3-contributor"


def base_url() -> str:
    return os.environ.get("MODEL_API_BASE_URL") or "https://api.meta.ai/v1"


def data_dir() -> Path:
    return Path(os.environ.get("HAQ_DATA_DIR") or SERVER_DIR / "workspace")


def today() -> date:
    """The date the agent treats as today. HAQ_TODAY (YYYY-MM-DD) pins it for tests and demos."""
    pinned = os.environ.get("HAQ_TODAY")
    return date.fromisoformat(pinned) if pinned else date.today()
