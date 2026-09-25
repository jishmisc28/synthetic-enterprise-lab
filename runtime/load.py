"""Generate (if needed) and load every source database from the estate files."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from psycopg2 import sql

from runtime.chaos import heal
from runtime.clock import DEFAULT_TODAY
from runtime.constants import DATABASES, PG_PASSWORD, PG_USER
from runtime.fileshape import drop_wave
from runtime.minio_landing import upload_landing
from runtime.pg import connect_cluster_admin, connect_source, target, wait_all
from runtime.relationships import build as build_relationships
from runtime.roles import apply_roles

ROOT = Path(os.environ.get("LAB_ROOT", "/opt/lab"))
DOMAIN = os.environ.get("DOMAIN", "aarohan")
ESTATE = Path(os.environ.get("ESTATE_DIR", f"/data/output/{DOMAIN}"))
SCALE = os.environ.get("SCALE", "tiny")
SEED = int(os.environ.get("SEED", "20260907"))
MINIO_OPTIONAL = os.environ.get("MINIO_OPTIONAL", "0") == "1"


SATELLITES = {
    "pay": {
        "schema": "pay",
        "tables": {
            "payment": (
                """
                CREATE TABLE pay.payment (
                    txn_ref text PRIMARY KEY,
                    utr text,
                    channel text,
                    status text,
                    amount numeric(19,4) NOT NULL,
                    event_date date,
                    value_date date,
                    settlement_date date,
                    ingested_at timestamptz,
                    loan_hint text,
                    mandate_id text
                )
                """,
                None,
                [
                    ("files/payments/upi.csv", True),
                    ("files/payments/nach.csv", False),
                    ("files/payments/neft.csv", False),
                    ("files/payments/cash.csv", False),
                ],
            ),
        },
    },
    "bureau": {
        "schema": "bureau",
        "tables": {
            "pull": (
                """
                CREATE TABLE bureau.pull (
                    bureau_id text PRIMARY KEY,
                    pan text,
                    score integer,
                    reported_as_of date,
                    enquiry_ref text,
                    cif_hint text,
                    active_tradelines integer,
                    enquiries_90d integer,
                    worst_dpd_24m integer,
                    reported_outstanding numeric(19,4)
                )
                """,
                "files/bureau/bureau_2026-07.csv",
                None,
            ),
        },
    },
    "coll": {
        "schema": "coll",
        "tables": {
            "event": (
                """
                CREATE TABLE coll.event (
                    event_id text PRIMARY KEY,
                    loan_ref text,
                    agent_code text,
                    kind text,
                    event_date date,
                    amount numeric(19,4)
                )
                """,
                "files/collections/events.csv",
                None,
            ),
            "incentive": (
                """
                CREATE TABLE coll.incentive (
                    incentive_id text PRIMARY KEY,
                    agent_code text,
                    loan_no text,
                    amount numeric(19,4),
                    paid_date date,
                    recovery_value_date date
                )
                """,
                "files/collections/incentives.csv",
                None,
            ),
        },
    },
    "gold": {
        "schema": "gold",
        "tables": {
            "packet": (
                """
                CREATE TABLE gold.packet (
                    packet_id text NOT NULL,
                    pledge_no text,
                    loan_no text,
                    kind text,
                    valuation_date date,
                    event_date date,
                    gross_g numeric(12,3),
                    net_g numeric(12,3),
                    purity text,
                    assessed_inr numeric(19,4),
                    custody_state text,
                    principal numeric(19,4),
                    proceeds_inr numeric(19,4),
                    PRIMARY KEY (packet_id, kind)
                )
                """,
                "files/gold/packets.csv",
                None,
            ),
        },
    },
    "veh": {
        "schema": "veh",
        "tables": {
            "commission": (
                """
                CREATE TABLE veh.commission (
                    commission_id text PRIMARY KEY,
                    loan_no text,
                    dealer_code text,
                    vin text,
                    invoice_no text,
                    amount numeric(19,4),
                    paid_date date,
                    disb_no text
                )
                """,
                "files/vehicle/commissions.csv",
                None,
            ),
        },
    },
    "crm": {
        "schema": "crm",
        "tables": {
            "account": (
                """
                CREATE TABLE crm.account (
                    account_number text PRIMARY KEY,
                    name text,
                    cif_hint text,
                    consent boolean
                )
                """,
                None,
                None,
            ),
            "campaign": (
                """
                CREATE TABLE crm.campaign (
                    offer_id text PRIMARY KEY,
                    cif text,
                    product_code text,
                    offered_on date,
                    account_number text
                )
                """,
                None,
                None,
            ),
        },
    },
    "gl": {
        "schema": "gl",
        "tables": {
            "journal": (
                """
                CREATE TABLE gl.journal (
                    je_id text PRIMARY KEY,
                    posted_date date,
                    account_code text,
                    amount numeric(19,4),
                    loan_ref text,
                    source text
                )
                """,
                "files/gl/journals.csv",
                None,
            ),
        },
    },
    "masters": {
        "schema": "masters",
        "tables": {
            "identity_override": (
                """
                CREATE TABLE masters.identity_override (
                    pan text PRIMARY KEY,
                    digital_cif text,
                    gold_cif text,
                    name_lms text,
                    name_gold text,
                    name_bureau text
                )
                """,
                "files/masters/identity_override.csv",
                None,
            ),
            "rule_set": (
                """
                CREATE TABLE masters.rule_set (
                    rule_code text NOT NULL,
                    product_code text NOT NULL,
                    effective_from date NOT NULL,
                    effective_to date,
                    payload jsonb NOT NULL,
                    PRIMARY KEY (rule_code, product_code, effective_from)
                )
                """,
                None,
                None,
            ),
        },
    },
}


def connect(source_key: str, dbname: str | None = None):
    """source_key is lms/pay/… — not a raw database name."""
    return connect_source(source_key, dbname=dbname)


def ensure_estate(force: bool = False) -> None:
    marker = ESTATE / "MANIFEST.json"
    if marker.exists() and not force:
        try:
            manifest = json.loads(marker.read_text())
            if manifest.get("scale") == SCALE and int(manifest.get("seed") or 0) == SEED:
                return
        except Exception:
            pass
        force = True
    if not force and (ESTATE / "verification.json").exists():
        return
    print(f"generating domain={DOMAIN} scale={SCALE} seed={SEED}", flush=True)
    sys.path.insert(0, str(ROOT / "domains"))
    if DOMAIN != "aarohan":
        raise SystemExit(f"no generator for domain {DOMAIN} yet")
    from aarohan.run import generate as generate_aarohan

    tmp = Path(f"/tmp/{DOMAIN}-estate")
    generate_aarohan(SCALE, SEED, tmp)
    ESTATE.mkdir(parents=True, exist_ok=True)
    for child in ESTATE.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    shutil.copytree(tmp, ESTATE, dirs_exist_ok=True)


def reset_db(source_key: str) -> None:
    spec_db = DATABASES[source_key]
    cluster = target(source_key)["cluster"]
    conn = connect_cluster_admin(cluster)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
            (spec_db,),
        )
        cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(spec_db)))
        cur.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
            sql.Identifier(spec_db), sql.Identifier(PG_USER)
        ))
    conn.close()


def load_lms() -> None:
    domain_sql = ROOT / "domains" / DOMAIN / "sql"
    schema = (domain_sql / "00_lms_schema.sql").read_text()
    rules = (domain_sql / "10_rules.sql").read_text()
    kpis = (domain_sql / "20_kpis.sql").read_text()
    t = target("lms")
    conn = connect("lms")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS lms CASCADE")
        cur.execute("DROP SCHEMA IF EXISTS fact CASCADE")
        cur.execute("DROP SCHEMA IF EXISTS metric CASCADE")
        cur.execute(schema)
        cur.execute(rules)
        cur.execute(kpis)
    conn.close()
    env = os.environ.copy()
    env.update({
        "PGHOST": t["host"],
        "PGPORT": str(t["port"]),
        "PGUSER": PG_USER,
        "PGPASSWORD": PG_PASSWORD,
        "PGDATABASE": t["dbname"],
    })
    load_sql = ROOT / "domains" / DOMAIN / "sql" / "load.sql"
    subprocess.check_call(
        ["psql", "-v", "ON_ERROR_STOP=1", "-f", str(load_sql)],
        cwd=str(ESTATE),
        env=env,
    )


def _copy_csv(cur, table: str, path: Path, header: bool = True) -> None:
    if not path.exists():
        print(f"skip missing {path}", flush=True)
        return
    with path.open("r", encoding="utf-8") as fh:
        if header:
            next(fh, None)
        cur.copy_expert(f"COPY {table} FROM STDIN WITH (FORMAT csv)", fh)


def load_satellites() -> None:
    for key, spec in SATELLITES.items():
        conn = connect(key)
        conn.autocommit = True
        schema = spec["schema"]
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            for table, (ddl, single, many) in spec["tables"].items():
                cur.execute(f"DROP TABLE IF EXISTS {schema}.{table} CASCADE")
                cur.execute(ddl)
                fq = f"{schema}.{table}"
                if single:
                    _copy_csv(cur, fq, ESTATE / single)
                if many:
                    first = True
                    for rel, is_first in many:
                        _copy_csv(cur, fq, ESTATE / rel, header=True)
                        first = is_first
                        _ = first
        conn.close()
    _load_crm()
    _load_master_rules()


def _load_crm() -> None:
    conn = connect("crm")
    conn.autocommit = True
    accounts = json.loads((ESTATE / "api" / "accounts.json").read_text()).get("records", [])
    campaigns = json.loads((ESTATE / "api" / "campaigns.json").read_text()).get("records", [])
    with conn.cursor() as cur:
        for rec in accounts:
            cur.execute(
                "INSERT INTO crm.account (account_number, name, cif_hint, consent) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (rec.get("AccountNumber"), rec.get("Name"), rec.get("cif_hint"), rec.get("consent", True)),
            )
        for rec in campaigns:
            cur.execute(
                "INSERT INTO crm.campaign (offer_id, cif, product_code, offered_on, account_number) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (rec.get("offer_id"), rec.get("cif"), rec.get("product_code"), rec.get("offered_on"), rec.get("account_number")),
            )
    conn.close()


def _load_master_rules() -> None:
    path = ESTATE / "files" / "masters" / "rule_set.json"
    rules = json.loads(path.read_text())
    conn = connect("masters")
    conn.autocommit = True
    with conn.cursor() as cur:
        for r in rules:
            cur.execute(
                """INSERT INTO masters.rule_set (rule_code, product_code, effective_from, effective_to, payload)
                   VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING""",
                (
                    r["rule_code"],
                    r["product_code"],
                    r["effective_from"],
                    r.get("effective_to"),
                    json.dumps(r.get("payload") or {}),
                ),
            )
    conn.close()


def maybe_minio() -> dict:
    if MINIO_OPTIONAL:
        return {"status": "skipped", "reason": "MINIO_OPTIONAL=1"}
    last = None
    for _ in range(20):
        try:
            return upload_landing()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1)
    return {"status": "degraded", "error": str(last)}


def main() -> int:
    reset = "--reset" in sys.argv
    force = "--force-generate" in sys.argv
    t0 = time.time()
    wait_all()
    ensure_estate(force=force)
    if reset:
        for key in DATABASES:
            reset_db(key)
    else:
        for key in DATABASES:
            try:
                connect(key).close()
            except Exception:
                reset_db(key)
    load_lms()
    load_satellites()
    roles = apply_roles()
    rel = build_relationships()
    drop_wave(0)  # remaining partner shapes arrive on a schedule from the events service
    minio = maybe_minio()
    # Reset world clock; advance(0) not allowed — write directly.
    clock_path = Path("/data/output/aarohan/stack/clock.json")
    clock_path.parent.mkdir(parents=True, exist_ok=True)
    clock_path.write_text(json.dumps({"today": DEFAULT_TODAY.isoformat()}, indent=2) + "\n")
    heal()
    elapsed = time.time() - t0
    report = {
        "ok": True,
        "scale": SCALE,
        "seed": SEED,
        "elapsed_s": round(elapsed, 3),
        "minio": minio,
        "roles": roles,
        "relationships": rel["answers"],
    }
    Path("/data/output/aarohan/stack/load_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
