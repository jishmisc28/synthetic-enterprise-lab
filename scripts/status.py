#!/usr/bin/env python3
"""One-screen estate status.  make status"""

from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "--profile", "minio"]
EXPECTED = ROOT / "domains" / "aarohan" / "expected" / "tiny" / "verification.json"
OUTPUT = ROOT / "output" / "aarohan" / "verification.json"

COUNTS = [
    ("S1 LMS         :55432", "postgres-lms", "aarohan_lms", "SELECT COUNT(*) FROM lms.loan_account"),
    ("S2 pay archive :55436", "postgres-archive", "aarohan_pay", "SELECT COUNT(*) FROM pay.payment"),
    ("S3 bureau arch :55436", "postgres-archive", "aarohan_bureau", "SELECT COUNT(*) FROM bureau.pull"),
    ("S4 Collections :55433", "postgres-coll", "aarohan_coll", "SELECT COUNT(*) FROM coll.event"),
    ("S5 Gold vault  :55435", "postgres-gold", "aarohan_gold", "SELECT COUNT(*) FROM gold.packet"),
    ("S6 veh archive :55436", "postgres-archive", "aarohan_veh", "SELECT COUNT(*) FROM veh.commission"),
    ("S7 crm archive :55436", "postgres-archive", "aarohan_crm", "SELECT COUNT(*) FROM crm.account"),
    ("S8 GL          :55434", "postgres-gl", "aarohan_gl", "SELECT COUNT(*) FROM gl.journal"),
    ("S9 masters arch:55436", "postgres-archive", "aarohan_masters", "SELECT COUNT(*) FROM masters.identity_override"),
]


def sh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True)


def psql_one(service: str, db: str, query: str) -> str:
    p = sh(
        COMPOSE
        + ["exec", "-T", "-e", "PGPASSWORD=aarohan", service, "psql", "-U", "aarohan", "-d", db, "-At", "-c", query]
    )
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "error").strip().splitlines()
        return "DOWN " + (err[-1] if err else f"exit {p.returncode}")
    return (p.stdout or "").strip() or "0"


def http_ok(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return f"up HTTP {resp.status}"
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None)
        return f"down {code or exc}"


def main() -> int:
    print("Synthetic Enterprise Lab status")
    print("-" * 72)
    for label, service, db, q in COUNTS:
        print(f"{label:24} {psql_one(service, db, q):>8} rows")

    landing = sorted(str(p.relative_to(ROOT / "output" / "landing")) for p in (ROOT / "output" / "landing").rglob("*") if p.is_file()) if (ROOT / "output" / "landing").exists() else []
    print(f"{'landing files':24} {len(landing):>8}  {landing}")

    mc = sh(
        COMPOSE
        + [
            "exec",
            "-T",
            "minio",
            "sh",
            "-c",
            "mc alias set local http://127.0.0.1:9000 aarohan aarohan-minio-dev >/dev/null && mc ls --recursive local/aarohan-landing",
        ]
    )
    objects = [ln.strip() for ln in (mc.stdout or "").splitlines() if ln.strip()]
    if mc.returncode != 0:
        print(f"{'minio aarohan-landing':24}     DOWN  {(mc.stderr or '')[:80]}")
    else:
        print(f"{'minio aarohan-landing':24} {len(objects):>8} objects")
        for ln in objects:
            print(f"  {ln}")

    print(f"{'ERP :18080':24} {http_ok('http://127.0.0.1:18080/health')}")
    print(f"{'events :18081 (pull)':24} {http_ok('http://127.0.0.1:18081/health')}")
    print(f"{'verify :18082':24} {http_ok('http://127.0.0.1:18082/health')}")
    print(f"{'minio :19000':24} {http_ok('http://127.0.0.1:19000/minio/health/live')}")

    print("-" * 72)
    if not OUTPUT.exists() or not EXPECTED.exists():
        print("verification.json: MISSING")
        return 1
    same = OUTPUT.read_bytes() == EXPECTED.read_bytes()
    print(f"verification.json vs expected/tiny: {'IDENTICAL' if same else 'DIFFER'}")
    if not same:
        return 1
    v = json.loads(OUTPUT.read_text())
    print(
        f"K1={v['kpis']['K1']['value']}  K2={v['kpis']['K2']['value']}  "
        f"K5={v['kpis']['K5']['value']}  K14={v['kpis']['K14']['value']} (event-kept; money-backed is 0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
