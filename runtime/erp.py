"""Mock ERP / core-banking HTTP. Pagination, auth, rate limit, occasional 500."""

from __future__ import annotations

import base64
import csv
import json
import os
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from runtime.chaos import load_chaos
from runtime.constants import AUTH_BEARER

ESTATE = Path(os.environ.get("ESTATE_DIR", "/data/output/aarohan"))
RATE_LIMIT = 40
WINDOW_S = 10.0
_hits: dict[str, list[float]] = defaultdict(list)
_fail_every = 0


app = FastAPI(title="Aarohan ERP mock")


def _auth(authorization: str | None) -> None:
    if authorization != f"Bearer {AUTH_BEARER}":
        raise HTTPException(status_code=401, detail="missing or invalid Authorization")


def _rate(ip: str) -> None:
    now = time.time()
    bucket = [t for t in _hits[ip] if now - t < WINDOW_S]
    if len(bucket) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="rate limit",
            headers={"Retry-After": "2"},
        )
    bucket.append(now)
    _hits[ip] = bucket


def _maybe_500() -> None:
    global _fail_every
    chaos = load_chaos()
    if chaos.get("erp-500"):
        raise HTTPException(
            status_code=500,
            detail="erp chaos: forced 500",
            headers={"Retry-After": "1"},
        )
    _fail_every += 1
    if _fail_every % 37 == 0:
        raise HTTPException(
            status_code=500,
            detail="transient erp fault",
            headers={"Retry-After": "1"},
        )


def _cursor_encode(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def _cursor_decode(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="bad cursor") from exc


def _read_csv(name: str) -> list[dict]:
    aliases = {
        "gl_journal.csv": ESTATE / "files" / "gl" / "journals.csv",
        "holiday_calendar.csv": ESTATE / "files" / "masters" / "holiday_calendar.csv",
        "rate_card.csv": ESTATE / "files" / "masters" / "rate_card.csv",
        "insurance_master.csv": ESTATE / "files" / "masters" / "insurance_master.csv",
        "charge_master.csv": ESTATE / "files" / "masters" / "charge_master.csv",
        "gl_account.csv": ESTATE / "files" / "masters" / "gl_account.csv",
        "product_catalog.csv": ESTATE / "files" / "masters" / "product_catalog.csv",
        "branch_hierarchy.csv": ESTATE / "files" / "masters" / "branch_hierarchy.csv",
        "dealer_map.csv": ESTATE / "files" / "masters" / "dealer_map.csv",
        "agent_hierarchy.csv": ESTATE / "files" / "masters" / "agent_hierarchy.csv",
        "identity_override.csv": ESTATE / "files" / "masters" / "identity_override.csv",
    }
    path = aliases.get(name, ESTATE / "files" / "masters" / name)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _page(rows: list[dict], cursor: str | None, limit: int) -> dict:
    offset = _cursor_decode(cursor)
    page = rows[offset : offset + limit]
    nxt = None
    if offset + limit < len(rows):
        nxt = _cursor_encode(offset + limit)
    return {"data": page, "next_cursor": nxt, "count": len(page), "total": len(rows)}


@app.middleware("http")
async def gates(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    # Raise-in-middleware becomes HTTP 500; return the status ourselves.
    auth = request.headers.get("authorization")
    if auth != f"Bearer {AUTH_BEARER}":
        return JSONResponse({"detail": "missing or invalid Authorization"}, status_code=401)
    try:
        _rate(request.client.host if request.client else "unknown")
        _maybe_500()
    except HTTPException as exc:
        return JSONResponse(
            {"detail": exc.detail},
            status_code=exc.status_code,
            headers=dict(exc.headers or {}),
        )
    return await call_next(request)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "erp", "chaos": load_chaos()}


@app.get("/gl/journals")
def journals(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    return JSONResponse(_page(_read_csv("gl_journal.csv"), cursor, limit))


@app.get("/masters/{kind}")
def masters(
    kind: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> JSONResponse:
    mapping = {
        "holidays": "holiday_calendar.csv",
        "rates": "rate_card.csv",
        "insurance": "insurance_master.csv",
        "charges": "charge_master.csv",
        "accounts": "gl_account.csv",
        "products": "product_catalog.csv",
        "branches": "branch_hierarchy.csv",
        "dealers": "dealer_map.csv",
        "agents": "agent_hierarchy.csv",
        "identity": "identity_override.csv",
    }
    filename = mapping.get(kind)
    if not filename:
        raise HTTPException(status_code=404, detail="unknown master")
    return JSONResponse(_page(_read_csv(filename), cursor, limit))


def _read_crm(name: str) -> list[dict]:
    path = ESTATE / "api" / name
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "data", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


@app.get("/crm/accounts")
def crm_accounts(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> JSONResponse:
    return JSONResponse(_page(_read_crm("accounts.json"), cursor, limit))


@app.get("/crm/campaigns")
def crm_campaigns(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> JSONResponse:
    return JSONResponse(_page(_read_crm("campaigns.json"), cursor, limit))
