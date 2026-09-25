"""Slack-shaped webhook sink. Records every POST for delivery proofs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

LOG = Path("/data/output/aarohan/stack/webhook.jsonl")
LOG.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Aarohan webhook sink")
_inbox: list[dict] = []


@app.post("/slack")
async def slack(request: Request) -> JSONResponse:
    body = await request.json()
    rec = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "headers": {
            "content-type": request.headers.get("content-type"),
            "user-agent": request.headers.get("user-agent"),
        },
        "body": body,
    }
    _inbox.append(rec)
    with LOG.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return JSONResponse({"ok": True, "id": len(_inbox)})


@app.get("/inbox")
def inbox() -> dict:
    return {"count": len(_inbox), "items": _inbox[-50:]}


@app.post("/reset")
def reset() -> dict:
    _inbox.clear()
    if LOG.exists():
        LOG.unlink()
    return {"ok": True}


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "webhook"}
