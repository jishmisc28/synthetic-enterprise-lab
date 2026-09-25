"""Source catalog: generic kinds + the active domain's instances."""

from __future__ import annotations

import os
import socket
from pathlib import Path

from runtime.pg import target

KIND_GUIDE = {
    "postgres": {
        "title": "Postgres (system of record)",
        "how": "One process per source that is a database. Never one database with many schemas.",
        "connect": "host, port, username, password, database, schema, dbtype=postgres",
    },
    "http-api": {
        "title": "HTTP / REST (vendor APIs)",
        "how": "Pagination, auth header, rate limits, occasional 500 + Retry-After.",
        "connect": "base URL + Authorization bearer. Cursor query param.",
    },
    "erp": {
        "title": "ERP / core-banking HTTP",
        "how": "The finance or core system the warehouse is a copy of. Cursors, 429, 500.",
        "connect": "base URL + bearer. Same data as the GL Postgres, different protocol.",
    },
    "saas": {
        "title": "SaaS (CRM, helpdesk, marketing)",
        "how": "Salesforce / HubSpot / Zendesk-shaped JSON over HTTP.",
        "connect": "HTTP JSON. Identity is a hint, not an FK.",
    },
    "events": {
        "title": "Event / stream HTTP",
        "how": "Pull only: GET and poll. POST /advance moves the clock. Does not POST to a client.",
        "connect": "base URL + bearer. GET /payments?since=. No push.",
    },
    "files": {
        "title": "Partner files",
        "how": "Not only CSV. xlsx with merged headers, jsonl, gzip, fixed-width, non-UTF-8.",
        "connect": "landing folder or S3/MinIO prefix. Drop on a schedule.",
    },
    "object-store": {
        "title": "Object store (S3)",
        "how": "Customer landing vs product archive are different buckets.",
        "connect": "endpoint, access key, secret, bucket, dated prefix.",
    },
    "mail": {
        "title": "Mail catcher",
        "how": "SMTP with no real provider keys. Proves case → owner → email.",
        "connect": "smtp host:port. No auth in this lab.",
    },
    "webhook": {
        "title": "Webhook sink",
        "how": "Slack-shaped POST body inbound. Not events pushed to the product.",
        "connect": "POST URL. Read GET /inbox.",
    },
}


def _archive_note(source_key: str) -> dict:
    t = target(source_key, from_host=True, role="ro")
    return {
        "host": t["host"],
        "port": t["port"],
        "database": t["dbname"],
        "schema": t["schema"],
        "username": t["user"],
        "password": t["password"],
        "note": "internal archive — not the client path",
    }


AAROHAN_SOURCES = [
    {
        "id": "s1-lms",
        "name": "LMS",
        "kind": "postgres",
        "role": "System of record for loans, customers, charges, rules",
        "protocol": "pgwire",
        "host": "127.0.0.1",
        "port": 55432,
        "database": "aarohan_lms",
        "schema": "lms",
        "username": "lms_ro",
        "password": "lms_ro_dev",
        "probe": {"type": "tcp", "host": "postgres-lms", "port": 5432},
        "model": "lms.customer, lms.loan_account, lms.instalment, lms.payment_applied, lms.rule_set, …",
        "join_notes": "Do not load payments here. Rules live in lms.rule_set.payload.",
    },
    {
        "id": "s2-pay",
        "name": "Payments file feed",
        "kind": "files",
        "role": "Bank / gateway / till files (S2)",
        "protocol": "s3",
        "endpoint": "http://127.0.0.1:19000",
        "bucket": "aarohan-landing",
        "prefix": "payments/",
        "auth": "S3 aarohan / aarohan-minio-dev",
        "probe": {"type": "http", "url": "http://minio:9000/minio/health/live"},
        "model": "dated keys payments/YYYY-MM-DD/*.csv.gz — txn_ref, utr, channel, amount, value_date",
        "join_notes": "Client path is MinIO + events pull. Postgres aarohan_pay is an internal archive.",
        "archive": _archive_note("pay"),
    },
    {
        "id": "s2-events",
        "name": "Payment events",
        "kind": "events",
        "role": "Pull-only replay of payments, collections, clickstream",
        "protocol": "http",
        "direction": "pull",
        "base_url": "http://127.0.0.1:18081",
        "auth": "Bearer aarohan-dev",
        "probe": {"type": "http", "url": "http://events:18081/health"},
        "model": "GET /payments /collections /clickstream  POST /advance?days=1",
        "join_notes": "Pull only. Does not POST to a client webhook. s2-late withholds last 2 days.",
    },
    {
        "id": "s3-bureau",
        "name": "Bureau",
        "kind": "files",
        "role": "Credit bureau as-of file",
        "protocol": "s3",
        "endpoint": "http://127.0.0.1:19000",
        "bucket": "aarohan-landing",
        "prefix": "bureau/",
        "auth": "S3 aarohan / aarohan-minio-dev",
        "probe": {"type": "http", "url": "http://minio:9000/minio/health/live"},
        "model": "bureau/YYYY-MM-DD/*.jsonl — pan, score, reported_as_of, cif_hint",
        "join_notes": "PAN is the steward. Postgres aarohan_bureau is an internal archive.",
        "archive": _archive_note("bureau"),
    },
    {
        "id": "s4-coll",
        "name": "Collections",
        "kind": "postgres",
        "role": "Agency attempts, PTP, incentives",
        "protocol": "pgwire",
        "host": "127.0.0.1",
        "port": 55433,
        "database": "aarohan_coll",
        "schema": "coll",
        "username": "coll_ro",
        "password": "coll_ro_dev",
        "probe": {"type": "tcp", "host": "postgres-coll", "port": 5432},
        "model": "coll.event, coll.incentive",
        "join_notes": "loan_ref = loan_no. Blank on walk-ins. Partner Excel is a landing overlay, not the book.",
    },
    {
        "id": "s5-gold",
        "name": "Gold vault",
        "kind": "postgres",
        "role": "Packets and custody (not the LMS pledge copy)",
        "protocol": "pgwire",
        "host": "127.0.0.1",
        "port": 55435,
        "database": "aarohan_gold",
        "schema": "gold",
        "username": "gold_ro",
        "password": "gold_ro_dev",
        "probe": {"type": "tcp", "host": "postgres-gold", "port": 5432},
        "model": "gold.packet (custody_state lives here only)",
        "join_notes": "pledge_no to lms.gold_pledge. Some packets have no pledge.",
    },
    {
        "id": "s6-vehicle",
        "name": "Dealer / vehicle",
        "kind": "files",
        "role": "Dealer commission partner file",
        "protocol": "s3",
        "endpoint": "http://127.0.0.1:19000",
        "bucket": "aarohan-landing",
        "prefix": "vehicle/",
        "auth": "S3 aarohan / aarohan-minio-dev",
        "probe": {"type": "http", "url": "http://minio:9000/minio/health/live"},
        "model": "vehicle/YYYY-MM-DD/commissions_partner.csv (cp1252)",
        "join_notes": "I07 is a commission that should not exist. Postgres aarohan_veh is an internal archive.",
        "archive": _archive_note("veh"),
    },
    {
        "id": "s7-crm",
        "name": "CRM",
        "kind": "saas",
        "role": "Accounts and campaign offers (Salesforce-shaped)",
        "protocol": "http",
        "base_url": "http://127.0.0.1:18080",
        "auth": "Bearer aarohan-dev",
        "probe": {"type": "http", "url": "http://erp:18080/health"},
        "model": "GET /crm/accounts /crm/campaigns (cursor). AccountNumber, cif_hint, offer_id",
        "join_notes": "cif_hint = cif. Postgres aarohan_crm is an internal archive.",
        "archive": _archive_note("crm"),
    },
    {
        "id": "s8-gl",
        "name": "General ledger",
        "kind": "postgres",
        "role": "Journal lines",
        "protocol": "pgwire",
        "host": "127.0.0.1",
        "port": 55434,
        "database": "aarohan_gl",
        "schema": "gl",
        "username": "gl_ro",
        "password": "gl_ro_dev",
        "probe": {"type": "tcp", "host": "postgres-gl", "port": 5432},
        "model": "gl.journal (je_id, posted_date, loan_ref, source)",
        "join_notes": "loan_ref is sparse. CASH_BATCH is T+1 vs LMS.",
    },
    {
        "id": "s8-erp",
        "name": "ERP / core-banking HTTP",
        "kind": "erp",
        "role": "Vendor-shaped GL + masters API",
        "protocol": "http",
        "base_url": "http://127.0.0.1:18080",
        "auth": "Bearer aarohan-dev",
        "probe": {"type": "http", "url": "http://erp:18080/health"},
        "model": "GET /gl/journals (cursor)  GET /masters/{products|branches|dealers|…}",
        "join_notes": "Same GL facts as s8-gl. Use this to test the connector, not another Postgres.",
    },
    {
        "id": "s9-masters",
        "name": "Masters / identity",
        "kind": "files",
        "role": "Identity override and dated rule copy for humans",
        "protocol": "s3",
        "endpoint": "http://127.0.0.1:19000",
        "bucket": "aarohan-landing",
        "prefix": "masters/",
        "auth": "S3 aarohan / aarohan-minio-dev",
        "probe": {"type": "http", "url": "http://minio:9000/minio/health/live"},
        "model": "masters/YYYY-MM-DD/identity_override.fwf; rule_set.json under the estate",
        "join_notes": "Typed rules live in lms.rule_set. Postgres aarohan_masters is an internal archive.",
        "archive": _archive_note("masters"),
    },
    {
        "id": "files-landing",
        "name": "Partner file landing",
        "kind": "files",
        "role": "What a partner actually emails or SFTP-drops",
        "protocol": "filesystem / s3",
        "path": "output/landing/",
        "probe": {"type": "files", "dir": "/data/landing"},
        "model": "gzip CSV, xlsx+total, jsonl, cp1252, fixed-width",
        "join_notes": "Waves land on a schedule, not all at once. Same bytes go to MinIO dated prefixes.",
    },
    {
        "id": "minio",
        "name": "Object store",
        "kind": "object-store",
        "role": "Customer landing + product archive",
        "protocol": "s3",
        "endpoint": "http://127.0.0.1:19000",
        "buckets": ["aarohan-landing", "archive"],
        "probe": {"type": "http", "url": "http://minio:9000/minio/health/live"},
        "optional": True,
        "model": "S3 keys under dated prefixes",
        "join_notes": "Stack runs with or without it. Down must say down. A zero is a lie.",
    },
    {
        "id": "mail",
        "name": "Mail catcher",
        "kind": "mail",
        "role": "Outbound case mail",
        "protocol": "smtp",
        "host": "127.0.0.1",
        "port": 18025,
        "ui": "http://127.0.0.1:18084",
        "probe": {"type": "tcp", "host": "mailpit", "port": 1025},
        "model": "SMTP messages, no provider key",
        "join_notes": "Use to prove a case reached its owner.",
    },
    {
        "id": "slack-sink",
        "name": "Webhook sink",
        "kind": "webhook",
        "role": "Slack-shaped posts inbound (product → Synthetic Enterprise Lab)",
        "protocol": "http",
        "base_url": "http://127.0.0.1:18083",
        "probe": {"type": "http", "url": "http://webhook:18083/health"},
        "model": "POST /slack  GET /inbox",
        "join_notes": "Not a push of Aarohan events. Direction is inbound.",
    },
]


def _tcp(host: str, port: int, timeout: float = 1.5) -> tuple[bool, str]:
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True, "open"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _http(url: str, timeout: float = 2.0) -> tuple[bool, str]:
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200, f"HTTP {resp.status}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:160]


def _files(dir_path: str) -> tuple[bool, str]:
    p = Path(dir_path)
    if not p.exists():
        return False, "missing"
    n = sum(1 for _ in p.rglob("*") if _.is_file())
    return n > 0, f"{n} files"


def probe(source: dict) -> dict:
    spec = source.get("probe") or {}
    kind = spec.get("type")
    if kind == "tcp":
        ok, detail = _tcp(spec["host"], int(spec["port"]))
    elif kind == "http":
        url = spec.get("url") or ""
        if os.environ.get("MINIO_OPTIONAL") == "1" and "minio" in url:
            return {"ok": True, "status": "skipped", "detail": "not in this topology"}
        if os.environ.get("MINIO_OPTIONAL") == "1" and source.get("optional"):
            return {"ok": True, "status": "skipped", "detail": "not in this topology"}
        ok, detail = _http(url)
    elif kind == "files":
        ok, detail = _files(spec["dir"])
    else:
        ok, detail = True, "no probe"
    return {"ok": ok, "status": "up" if ok else "down", "detail": detail}


def snapshot() -> dict:
    domain = os.environ.get("DOMAIN", "aarohan")
    sources = []
    for src in AAROHAN_SOURCES:
        row = dict(src)
        row["health"] = probe(src)
        sources.append(row)
    down = [s["id"] for s in sources if not s["health"]["ok"] and not s.get("optional")]
    return {
        "product": "Synthetic Enterprise Lab",
        "domain": domain,
        "domain_title": "Aarohan Finance (fintech / NBFC lending)",
        "kinds": KIND_GUIDE,
        "sources": sources,
        "ok": not down,
        "down": down,
    }
