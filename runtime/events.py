"""Payment / collection / clickstream event service. Replay + live + advance."""

from __future__ import annotations

import csv
import os
import threading
import time
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from runtime.chaos import load_chaos
from runtime.clock import advance as advance_clock
from runtime.clock import load_clock
from runtime.constants import AUTH_BEARER
from runtime.fileshape import drop_wave
from runtime.minio_landing import upload_one

ESTATE = Path(os.environ.get("ESTATE_DIR", "/data/output/aarohan"))
app = FastAPI(title="Aarohan events")


def _schedule_partner_files() -> None:
    """Waves 1–4 land after up, not in the same second as wave 0."""

    def _run() -> None:
        for wave, wait in ((1, 3), (2, 3), (3, 3), (4, 3)):
            time.sleep(wait)
            try:
                for path in drop_wave(wave):
                    upload_one(Path(path))
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()


@app.on_event("startup")
def _startup() -> None:
    _schedule_partner_files()


def _auth(authorization: str | None) -> None:
    if authorization != f"Bearer {AUTH_BEARER}":
        raise HTTPException(status_code=401, detail="missing or invalid Authorization")


def _rows(name: str) -> list[dict]:
    """name is payments | collections | clickstream. Payments are four channel files."""
    if name == "payments.csv":
        rows: list[dict] = []
        for ch in ("upi.csv", "nach.csv", "neft.csv", "cash.csv"):
            path = ESTATE / "files" / "payments" / ch
            if path.exists():
                with path.open(newline="", encoding="utf-8") as fh:
                    rows.extend(csv.DictReader(fh))
        return rows
    mapping = {
        "collections.csv": ESTATE / "files" / "collections" / "events.csv",
        "clickstream.csv": ESTATE / "files" / "collections" / "events.csv",
    }
    path = mapping.get(name)
    if not path or not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _as_of(rows: list[dict], today: date, date_col: str) -> list[dict]:
    chaos = load_chaos()
    cutoff = today
    if chaos.get("s2-late"):
        # Payments posted in the last 2 days have not arrived yet.
        from datetime import timedelta

        cutoff = today - timedelta(days=2)
    out = []
    for row in rows:
        raw = row.get(date_col) or row.get("event_date") or ""
        if not raw:
            continue
        if date.fromisoformat(raw[:10]) <= cutoff:
            out.append(row)
    return out


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "events",
        "direction": "pull",
        "today": load_clock().isoformat(),
        "chaos": load_chaos(),
    }


@app.get("/payments")
def payments(
    authorization: str | None = Header(default=None),
    since: str | None = Query(default=None),
    live: bool = Query(default=False),
) -> JSONResponse:
    _auth(authorization)
    today = load_clock()
    rows = _as_of(_rows("payments.csv"), today, "event_date")
    if since:
        rows = [r for r in rows if (r.get("event_date") or "") >= since]
    if live:
        rows = [r for r in rows if (r.get("event_date") or "") == today.isoformat()]
    return JSONResponse({"today": today.isoformat(), "count": len(rows), "data": rows})


@app.get("/collections")
def collections(authorization: str | None = Header(default=None)) -> JSONResponse:
    _auth(authorization)
    today = load_clock()
    rows = _as_of(_rows("collections.csv"), today, "event_date")
    return JSONResponse({"today": today.isoformat(), "count": len(rows), "data": rows})


@app.get("/clickstream")
def clickstream(authorization: str | None = Header(default=None)) -> JSONResponse:
    _auth(authorization)
    today = load_clock()
    rows = _as_of(_rows("clickstream.csv"), today, "event_date")
    screens = {
        "PTP_MADE": "promise_to_pay",
        "PTP_KEPT": "receipt",
        "CALL": "dialer",
        "VISIT": "field_app",
        "SMS": "notify",
    }
    click = []
    for r in rows:
        click.append({
            "session_id": f"CLK-{r.get('event_id')}",
            "cif": "",
            "event_name": r.get("kind"),
            "screen": screens.get(r.get("kind") or "", "home"),
            "event_date": r.get("event_date"),
            "posted_at": r.get("event_date"),
            "device": "android",
            "app_version": "3.4.0",
            "loan_ref": r.get("loan_ref"),
        })
    return JSONResponse({"today": today.isoformat(), "count": len(click), "data": click})


@app.post("/advance")
def advance(days: int = Query(default=1, ge=1, le=90), authorization: str | None = Header(default=None)) -> dict:
    _auth(authorization)
    today = advance_clock(days)
    # A presenter moving the world also drops the next partner file wave.
    dropped = drop_wave(min(days, 4))
    uploaded = []
    for path in dropped:
        uploaded.extend(upload_one(Path(path)))
    return {"ok": True, "today": today.isoformat(), "dropped": dropped, "minio": uploaded}


@app.get("/clock")
def clock() -> dict:
    return {"today": load_clock().isoformat()}
