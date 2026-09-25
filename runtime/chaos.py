from __future__ import annotations

import json
from pathlib import Path

from runtime.constants import CHAOS_PATH


def load_chaos() -> dict:
    path = Path(CHAOS_PATH)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def set_flag(name: str, value: bool) -> dict:
    path = Path(CHAOS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = load_chaos()
    current[name] = value
    path.write_text(json.dumps(current, indent=2) + "\n")
    return current


def heal() -> dict:
    path = Path(CHAOS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    empty: dict = {}
    path.write_text("{}\n")
    return empty
