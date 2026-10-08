"""Everything the pipeline needs from outside: model access and where files live.

Values come from the environment, or from a .env file in the project folder (see .env.example); the environment
wins. Paths default to the project folders.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    model: str
    base_url: str
    api_key: str
    data_dir: Path
    storage_dir: Path
    root: Path = ROOT


def _read_env_file() -> None:
    try:
        lines = (ROOT / ".env").read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        m = re.match(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if m and not m.group(1).startswith("#"):
            value = re.sub(r"""^(['"])(.*)\1$""", r"\2", m.group(2))
            os.environ.setdefault(m.group(1), value)


def load_config() -> Config:
    _read_env_file()
    return Config(
        model=os.environ.get("MODEL", "swiss-ai/Apertus-v1.5-8B"),
        base_url=os.environ.get("BASE_URL", "https://api.inference.cscs.ch/v1"),
        api_key=os.environ.get("API_KEY", ""),
        data_dir=Path(os.environ.get("DATA_DIR", ROOT / "data")),
        storage_dir=Path(os.environ.get("STORAGE_DIR", ROOT / "storage")),
    )
