#!/usr/bin/env python3
"""Prove source isolation. Run from the repo root:  make prove-separation

Shows nine DSNs, cross-database errors from LMS, I01 three-store disagreement,
then minio-down while Postgres still answers, then heal.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "--profile", "minio"]

# Must match runtime/pg.py. Duplicated so this script runs without psycopg2 on the host.
DSNS = [
    ("S1 LMS        client ", "lms_ro    @ 127.0.0.1:55432 / aarohan_lms   schema=lms"),
    ("S2 Payments   archive", "pay_ro    @ 127.0.0.1:55436 / aarohan_pay   schema=pay"),
    ("S3 Bureau     archive", "bureau_ro @ 127.0.0.1:55436 / aarohan_bureau schema=bureau"),
    ("S4 Collections client", "coll_ro   @ 127.0.0.1:55433 / aarohan_coll  schema=coll"),
    ("S5 Gold vault client ", "gold_ro   @ 127.0.0.1:55435 / aarohan_gold  schema=gold"),
    ("S6 Dealer     archive", "veh_ro    @ 127.0.0.1:55436 / aarohan_veh   schema=veh"),
    ("S7 CRM        archive", "crm_ro    @ 127.0.0.1:55436 / aarohan_crm   schema=crm  (client path is HTTP :18080/crm)"),
    ("S8 GL         client ", "gl_ro     @ 127.0.0.1:55434 / aarohan_gl    schema=gl"),
    ("S9 Masters    archive", "masters_ro@ 127.0.0.1:55436 / aarohan_masters schema=masters"),
]


def sh(args: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=check)


def psql(service: str, db: str, query: str, user: str = "aarohan", password: str = "aarohan") -> subprocess.CompletedProcess:
    return sh(
        COMPOSE
        + [
            "exec",
            "-T",
            "-e",
            f"PGPASSWORD={password}",
            service,
            "psql",
            "-U",
            user,
            "-d",
            db,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            query,
        ]
    )


def section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def show(proc: subprocess.CompletedProcess) -> None:
    out = (proc.stdout or "").rstrip()
    err = (proc.stderr or "").rstrip()
    if out:
        print(out)
    if err:
        print(err)
    if proc.returncode != 0 and not err and not out:
        print(f"(exit {proc.returncode})")


def main() -> int:
    print("Synthetic Enterprise Lab prove-separation")
    print(f"cwd={ROOT}")

    section("1. Nine connection strings (client vs internal archive)")
    for label, dsn in DSNS:
        print(f"  {label}  {dsn}")

    section("2. Query from S1 LMS cannot see S5 gold.packet or S8 gl.journal")
    print("-- as lms_ro on postgres-lms / aarohan_lms --")
    show(psql("postgres-lms", "aarohan_lms", "SELECT COUNT(*) FROM gold.packet;", user="lms_ro", password="lms_ro_dev"))
    show(psql("postgres-lms", "aarohan_lms", "SELECT COUNT(*) FROM gl.journal;", user="lms_ro", password="lms_ro_dev"))
    print("-- lms_ro CONNECT to aarohan_gl on the LMS process (database is not there) --")
    show(psql("postgres-lms", "aarohan_gl", "SELECT 1;", user="lms_ro", password="lms_ro_dev"))
    print("-- lms_ro password against the GL process (role does not exist there) --")
    show(psql("postgres-gl", "aarohan_gl", "SELECT 1;", user="lms_ro", password="lms_ro_dev"))

    section("3. I01 — one loan, three stores, intended disagreement")
    print("S1 lms.payment_applied for AF-LN-I01-PL / UPI-I01-8891 (expect 0 rows)")
    show(
        psql(
            "postgres-lms",
            "aarohan_lms",
            "SELECT lms_receipt_no, loan_no, amount, ext_txn_ref "
            "FROM lms.payment_applied "
            "WHERE loan_no = 'AF-LN-I01-PL' OR ext_txn_ref IN ('UPI-I01-8891','RBIUPI00I01A');",
        )
    )
    print("S2 pay.payment UPI-I01-8891 (expect SUCCESS 6052.1400 2026-08-03)")
    show(
        psql(
            "postgres-archive",
            "aarohan_pay",
            "SELECT txn_ref, status, amount, event_date, value_date, loan_hint "
            "FROM pay.payment WHERE txn_ref = 'UPI-I01-8891';",
        )
    )
    print("S8 gl.journal JE-I01 (expect 6052.1400 2026-08-04 CASH_BATCH, loan_ref empty)")
    show(
        psql(
            "postgres-gl",
            "aarohan_gl",
            "SELECT je_id, posted_date, amount, loan_ref, source "
            "FROM gl.journal WHERE je_id = 'JE-I01';",
        )
    )
    print("S1 loan still overdue on the book")
    show(
        psql(
            "postgres-lms",
            "aarohan_lms",
            "SELECT loan_no, status, dpd, principal FROM lms.loan_account WHERE loan_no = 'AF-LN-I01-PL';",
        )
    )

    section("4. minio-down — file feed is down; Postgres sources still answer")
    broke = sh(["make", "break", "minio-down"])
    print((broke.stdout or broke.stderr or "").strip())
    live = sh(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:19000/minio/health/live"])
    print(f"minio live probe HTTP {live.stdout or live.returncode} (expect not 200)")
    print("S1 LMS still answers:")
    show(psql("postgres-lms", "aarohan_lms", "SELECT COUNT(*) AS loans FROM lms.loan_account;"))
    print("S8 GL still answers:")
    show(psql("postgres-gl", "aarohan_gl", "SELECT COUNT(*) AS journals FROM gl.journal;"))
    print("S4 Collections still answers:")
    show(psql("postgres-coll", "aarohan_coll", "SELECT COUNT(*) AS events FROM coll.event;"))
    print("heal")
    healed = sh(["make", "heal"])
    print((healed.stdout or healed.stderr or "").strip())
    live2 = sh(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:19000/minio/health/live"])
    print(f"minio live probe after heal HTTP {live2.stdout}")

    section("Done")
    print("A zero from MinIO while it is down would be a lie. The probe above is the status.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
