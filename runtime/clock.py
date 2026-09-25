from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from runtime.constants import CLOCK_PATH

DEFAULT_TODAY = date(2026, 9, 7)


def load_clock() -> date:
    path = Path(CLOCK_PATH)
    if not path.exists():
        return DEFAULT_TODAY
    payload = json.loads(path.read_text())
    return date.fromisoformat(payload["today"])


def advance(days: int) -> date:
    today = load_clock() + timedelta(days=days)
    path = Path(CLOCK_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"today": today.isoformat()}, indent=2) + "\n")
    return today
