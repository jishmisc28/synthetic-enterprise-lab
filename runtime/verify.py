"""Expect endpoints + full stack verification against verification.json."""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from runtime.catalog import snapshot
from runtime.chaos import heal, load_chaos, set_flag
from runtime.clock import load_clock
from runtime.constants import AUTH_BEARER, DATABASES
from runtime.pg import connect_source
from runtime.fileshape import waves_present

ESTATE = Path(os.environ.get("ESTATE_DIR", "/data/output/aarohan"))
MINIO_OPTIONAL = os.environ.get("MINIO_OPTIONAL", "0") == "1"
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
STATIC = Path(os.environ.get("LAB_STATIC", "/opt/lab/static"))

app = FastAPI(title="Synthetic Enterprise Lab health")


def _verification() -> dict:
    path = ESTATE / "verification.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="verification.json missing — run the loader")
    return json.loads(path.read_text())


def _ground_truth() -> list:
    path = ESTATE / "ground_truth.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _pg(source_key: str):
    return connect_source(source_key)


def _fetch(url: str, headers: dict | None = None, timeout: float = 3.0) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


@app.get("/", response_class=HTMLResponse)
def home() -> FileResponse:
    page = STATIC / "index.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="health page missing")
    return FileResponse(page)


@app.get("/catalog")
def catalog() -> dict:
    return snapshot()


@app.get("/healthz")
def healthz() -> dict:
    snap = snapshot()
    return {
        "ok": snap["ok"],
        "product": "synthetic-enterprise-lab",
        "domain": snap["domain"],
        "down": snap["down"],
        "today": load_clock().isoformat(),
        "chaos": load_chaos(),
        "sources": {s["id"]: s["health"] for s in snap["sources"]},
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "verify", "today": load_clock().isoformat(), "chaos": load_chaos()}


@app.get("/expect/kpi/{kpi_id}")
def expect_kpi(kpi_id: str) -> dict:
    v = _verification()
    kid = kpi_id.upper()
    if kid not in v["kpis"]:
        raise HTTPException(status_code=404, detail=f"unknown kpi {kid}")
    return v["kpis"][kid]


@app.get("/expect/monitor/{monitor_id}")
def expect_monitor(monitor_id: str) -> dict:
    v = _verification()
    mid = monitor_id.upper()
    if mid not in v["monitors"]:
        raise HTTPException(status_code=404, detail=f"unknown monitor {mid}")
    m = v["monitors"][mid]
    return {
        "id": mid,
        "must_breach": m["must"],
        "must_not": m["must_not"],
        "observed": m["observed"],
        "near_misses_that_must_not": m["must_not"],
        "owner": m.get("owner"),
        "count": m["count"],
    }


@app.get("/expect/ground-truth")
def expect_gt() -> dict:
    return {"count": len(_ground_truth()), "rows": _ground_truth()}


@app.get("/relationships")
def relationships() -> dict:
    path = Path("/data/output/aarohan/stack/relationships.json")
    if not path.exists():
        raise HTTPException(status_code=503, detail="relationships not built")
    return json.loads(path.read_text())


@app.post("/chaos/{flag}")
def chaos_on(flag: str) -> dict:
    allowed = {"lms-slow", "s2-late", "erp-500", "minio-down"}
    if flag not in allowed:
        raise HTTPException(status_code=400, detail=f"unknown flag; try {sorted(allowed)}")
    return set_flag(flag, True)


@app.post("/heal")
def chaos_heal() -> dict:
    return heal()


def _sql_one(dbname: str, q: str):
    conn = _pg(dbname)
    try:
        with conn.cursor() as cur:
            cur.execute(q)
            return cur.fetchone()
    finally:
        conn.close()


def _sql_all(dbname: str, q: str):
    conn = _pg(dbname)
    try:
        with conn.cursor() as cur:
            cur.execute(q)
            return cur.fetchall()
    finally:
        conn.close()


def _money(v) -> str:
    return f"{Decimal(str(v)):.4f}"


def run_verify() -> dict:
    checks: list[dict] = []
    v = _verification()
    chaos = load_chaos()

    def add(name: str, ok: bool, detail: str, required: bool = True) -> None:
        checks.append({"check": name, "ok": ok, "detail": detail, "required": required})

    # --- reachability ---
    for key, db in DATABASES.items():
        try:
            conn = _pg(key)
            conn.close()
            add(f"pg:{key}", True, f"{db} reachable")
        except Exception as exc:  # noqa: BLE001
            add(f"pg:{key}", False, str(exc))

    for name, url, hdrs in (
        ("erp", "http://erp:18080/health", None),
        ("events", "http://events:18081/health", None),
        ("webhook", "http://webhook:18083/health", None),
    ):
        status, body = _fetch(url, hdrs)
        add(name, status == 200, f"HTTP {status} {body[:160]}")

    # Mailpit's HTTP UI can hang across the compose bridge; SMTP is the delivery path.
    try:
        sock = socket.create_connection(("mailpit", 1025), timeout=3)
        sock.close()
        add("mailpit", True, "SMTP :1025 open (UI :18084 on the host)")
    except Exception as exc:  # noqa: BLE001
        add("mailpit", False, f"SMTP :1025 unreachable: {exc}")

    # ERP authenticated page
    st, body = _fetch("http://erp:18080/gl/journals?limit=1", {"Authorization": f"Bearer {AUTH_BEARER}"})
    if chaos.get("erp-500"):
        add("erp-data", st == 500, f"chaos erp-500: HTTP {st} — report the source error, do not substitute a zero", required=True)
    else:
        add("erp-data", st == 200, f"HTTP {st} {body[:120]}")

    st, body = _fetch("http://events:18081/payments?live=false", {"Authorization": f"Bearer {AUTH_BEARER}"})
    add("events-data", st == 200, f"HTTP {st}")

    # MinIO
    if MINIO_OPTIONAL:
        add("minio", True, "not in topology (nominio). Product object-store paths are untested.", required=False)
    else:
        st, body = _fetch(MINIO_ENDPOINT + "/minio/health/live")
        if chaos.get("minio-down") or st != 200:
            add(
                "minio",
                False,
                (
                    "minio-down: buckets aarohan-landing and archive are unreachable. "
                    "Report the object store as down. Do not substitute a zero. "
                    f"probe={st} {body[:120]}"
                ),
            )
        else:
            add("minio", True, "landing + archive endpoints alive")

    # --- loaded LMS vs generator ---
    try:
        loans = _sql_one("lms", "SELECT count(*) FROM lms.loan_account")[0]
        customers = _sql_one("lms", "SELECT count(*) FROM lms.customer")[0]
        instalments = _sql_one("lms", "SELECT count(*) FROM lms.instalment")[0]
        rules = _sql_one("lms", "SELECT count(*) FROM lms.rule_set")[0]
        npa_null = _sql_one("lms", "SELECT count(*) FROM lms.loan_account WHERE npa_flag IS NULL")[0]
        products = _sql_one("lms", "SELECT count(*) FROM lms.product")[0]
        branches = _sql_one("lms", "SELECT count(*) FROM lms.branch")[0]
        add("row:loans", loans == v["cleaning"]["loans"], f"{loans} vs expected {v['cleaning']['loans']}")
        add("row:customers", customers == v["cleaning"]["customers"], f"{customers} vs expected {v['cleaning']['customers']}")
        add("row:instalments", instalments == v["cleaning"]["instalments"], f"{instalments} vs expected {v['cleaning']['instalments']}")
        add("row:rule_set", rules >= 31, f"{rules} dated rules (must be ≥31; empty rule_set is a failed pack)")
        add("row:npa_flag", npa_null == 0, f"{npa_null} NULL npa_flag (must be 0)")
        add("row:product", products >= 6, f"{products} products loaded (FK parent)")
        add("row:branch", branches >= 32, f"{branches} branches loaded (FK parent)")
        pay = _sql_one("pay", "SELECT count(*) FROM pay.payment")[0]
        add("row:s2", pay == v["cleaning"]["s2_payments"], f"{pay} vs expected {v['cleaning']['s2_payments']}")
        gold = _sql_one("gold", "SELECT count(*) FROM gold.packet")[0]
        add("row:gold", gold == v["cleaning"]["gold_ops"], f"{gold} vs expected {v['cleaning']['gold_ops']}")
        gl = _sql_one("gl", "SELECT count(*) FROM gl.journal")[0]
        add("row:gl", gl == v["cleaning"]["gl_lines"], f"{gl} vs expected {v['cleaning']['gl_lines']}")
        coll = _sql_one("coll", "SELECT count(*) FROM coll.event")[0]
        add("row:coll", coll == v["cleaning"]["collection_events"], f"{coll} vs expected {v['cleaning']['collection_events']}")
    except Exception as exc:  # noqa: BLE001
        add("row-counts", False, str(exc))

    # --- two KPIs from SQL (proves the load, not just the JSON) ---
    try:
        k1 = _sql_one(
            "lms",
            "SELECT COALESCE(SUM(amount),0) FROM lms.disbursement "
            "WHERE disb_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'",
        )[0]
        add("kpi:K1", _money(k1) == v["kpis"]["K1"]["value"], f"sql={_money(k1)} expected={v['kpis']['K1']['value']}")

        due = _sql_one(
            "lms",
            "SELECT COALESCE(SUM(amount),0) FROM lms.instalment "
            "WHERE due_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'",
        )[0]
        s2 = _sql_one(
            "pay",
            "SELECT COALESCE(SUM(amount),0) FROM pay.payment "
            "WHERE status = 'SUCCESS' AND value_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'",
        )[0]
        k5 = (Decimal(str(s2)) / Decimal(str(due))) if due else Decimal("0")
        got = f"{float(k5):.4f}"
        add("kpi:K5", got == v["kpis"]["K5"]["value"], f"sql={got} expected={v['kpis']['K5']['value']} (S2/due, not LMS applied)")
    except Exception as exc:  # noqa: BLE001
        add("kpi-sql", False, str(exc))

    # --- every KPI / monitor in verification.json ---
    for kid, exp in v["kpis"].items():
        add(f"expect:kpi:{kid}", True, json.dumps(exp.get("value") if exp.get("shape") == "AM" else exp.get("row_count")))
    for mid, exp in v["monitors"].items():
        missing = [k for k in exp["must"] if k not in exp["observed"]]
        leaked = [k for k in exp["must_not"] if k in exp["observed"]]
        add(
            f"monitor:{mid}",
            not missing and not leaked,
            f"must={exp['must']} must_not={exp['must_not']} observed={exp['observed']}"
            + (f" MISSING {missing}" if missing else "")
            + (f" LEAKED {leaked}" if leaked else ""),
        )

    # M1 from loaded tables (cross-database, in the verifier — not a silent join)
    try:
        overdue = {r[0] for r in _sql_all("lms", "SELECT DISTINCT loan_no FROM lms.instalment WHERE status = 'OVERDUE'")}
        applied = {r[0] for r in _sql_all("lms", "SELECT ext_txn_ref FROM lms.payment_applied WHERE ext_txn_ref IS NOT NULL")}
        s2_rows = _sql_all(
            "pay",
            "SELECT txn_ref, utr, loan_hint FROM pay.payment WHERE status = 'SUCCESS' AND value_date <= DATE '2026-08-31'",
        )
        m1 = []
        for txn_ref, utr, hint in s2_rows:
            if {txn_ref, utr} & applied:
                continue
            if hint in overdue:
                m1.append(hint)
        must = set(v["monitors"]["M1"]["must"])
        must_not = set(v["monitors"]["M1"]["must_not"])
        add("sql:M1", must.issubset(set(m1)) and not (must_not & set(m1)), f"observed={m1}")
    except Exception as exc:  # noqa: BLE001
        add("sql:M1", False, str(exc))

    waves = waves_present()
    add("files:landing", len(waves) >= 4, f"partner files present: {waves}")

    failed = [c for c in checks if c["required"] and not c["ok"]]
    return {
        "ok": not failed,
        "today": load_clock().isoformat(),
        "chaos": chaos,
        "scale": v.get("scale"),
        "seed": v.get("seed"),
        "failed": failed,
        "checks": checks,
    }


@app.get("/verify")
def verify() -> JSONResponse:
    report = run_verify()
    return JSONResponse(report, status_code=200 if report["ok"] else 503)
