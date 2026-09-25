"""Aarohan estate runner. Entry point: generate(scale, seed, out)."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .constants import CLOSE_DATE, ESTATE_TODAY, SEED
from .emit import emit, jsonable
from .estate import build_estate
from .evaluate import evaluate, sha256_file, write_verification_md
from .rules import RULES

ROOT = Path(__file__).resolve().parent


def generate(scale: str, seed: int, out: Path) -> dict:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    estate = build_estate(scale, seed)
    emit(estate, out)

    schema = (ROOT / "sql" / "00_lms_schema.sql").read_text(encoding="utf-8")
    (out / "lms" / "00_lms_schema.sql").write_text(schema, encoding="utf-8")
    if "CREATE TABLE lms.payment_gateway_raw" in schema:
        raise SystemExit("lms schema must not contain payment_gateway_raw")
    if "custody_state" in schema.split("CREATE TABLE lms.gold_pledge")[1].split(";")[0]:
        raise SystemExit("lms.gold_pledge must not contain custody_state")

    rules_src = ROOT / "rules" / "rule_set.json"
    if rules_src.exists():
        (out / "files" / "masters" / "rule_set.json").write_text(
            rules_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
    else:
        (out / "files" / "masters" / "rule_set.json").write_text(
            json.dumps(jsonable(RULES), indent=2) + "\n", encoding="utf-8"
        )
    rule_sha = sha256_file(out / "files" / "masters" / "rule_set.json")

    verification = evaluate(estate)
    (out / "verification.json").write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out / "VERIFICATION.md").write_text(write_verification_md(verification), encoding="utf-8")

    gt_path = out / "ground_truth.json"
    gt_sha = sha256_file(gt_path)

    missing = []
    leaked = []
    for mid, m in verification["monitors"].items():
        for key in m["must"]:
            if key not in m["observed"]:
                missing.append(f"{mid}:{key}")
        for key in m["must_not"]:
            if key in m["observed"]:
                leaked.append(f"{mid}:{key}")
    if missing:
        raise SystemExit(f"monitors missing named keys: {missing}")
    if leaked:
        raise SystemExit(f"near-miss leaked into observed: {leaked}")
    if "AF-LN-M4-ZERO" in verification["monitors"]["M4"]["observed"]:
        raise SystemExit("M4 must not fire on AF-LN-M4-ZERO")

    valid_ids = set(verification["incidents"]["valid"])
    for i in range(1, 16):
        if f"I{i:02d}" not in valid_ids:
            raise SystemExit(f"missing valid incident I{i:02d}")

    manifest = {
        "seed": seed or SEED,
        "scale": scale,
        "estate": "aarohan",
        "generator": "domains/aarohan/run.py",
        "domain": "aarohan-lending",
        "estate_today": ESTATE_TODAY.isoformat(),
        "close_date": CLOSE_DATE.isoformat(),
        "customers": verification["cleaning"]["customers"],
        "loans": verification["cleaning"]["loans"],
        "instalments": verification["cleaning"]["instalments"],
        "s2_payments": verification["cleaning"]["s2_payments"],
        "rule_set_sha256": rule_sha,
        "ground_truth_sha256": gt_sha,
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
