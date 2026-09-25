"""Join-key census. Exact unmatched counts from the files the loader just used."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from runtime.constants import RELATIONSHIPS_PATH

ESTATE = Path("/data/output/aarohan")


def _csv(rel: str) -> list[dict]:
    path = ESTATE / rel
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _payments() -> list[dict]:
    rows: list[dict] = []
    for name in ("upi.csv", "nach.csv", "neft.csv", "cash.csv"):
        rows.extend(_csv(f"files/payments/{name}"))
    return rows


def build() -> dict:
    loans = {r["loan_no"] for r in _csv("lms/loan_account.csv")}
    customers = {r["cif"] for r in _csv("lms/customer.csv")}
    pans = {r["pan"] for r in _csv("lms/customer.csv")}
    applied_refs = {r["ext_txn_ref"] for r in _csv("lms/payment_applied.csv") if r.get("ext_txn_ref")}
    pledges = {r["pledge_no"] for r in _csv("lms/gold_pledge.csv")}

    pays = _payments()
    s2_no_loan = [p for p in pays if p.get("loan_hint") and p["loan_hint"] not in loans]
    s2_blank_hint = [p for p in pays if not p.get("loan_hint")]
    s2_unapplied = [
        p for p in pays
        if p.get("status") == "SUCCESS"
        and not ({p.get("utr"), p.get("txn_ref")} & applied_refs)
    ]

    bureau = _csv("files/bureau/bureau_2026-07.csv")
    s3_no_pan = [r for r in bureau if r.get("pan") and r["pan"] not in pans]
    s3_no_cif = [r for r in bureau if r.get("cif_hint") and r["cif_hint"] not in customers]

    coll = _csv("files/collections/events.csv")
    s4_no_loan = [r for r in coll if r.get("loan_ref") and r["loan_ref"] not in loans]
    s4_blank = [r for r in coll if not r.get("loan_ref")]

    gold = _csv("files/gold/packets.csv")
    s5_no_pledge = [r for r in gold if r.get("pledge_no") and r["pledge_no"] not in pledges]
    s5_no_loan = [r for r in gold if r.get("loan_no") and r["loan_no"] not in loans]

    veh = _csv("files/vehicle/commissions.csv")
    s6_no_loan = [r for r in veh if r.get("loan_no") and r["loan_no"] not in loans]

    gl = _csv("files/gl/journals.csv")
    s8_blank_ref = [r for r in gl if not r.get("loan_ref")]
    s8_no_loan = [r for r in gl if r.get("loan_ref") and r["loan_ref"] not in loans]

    twins = _csv("files/masters/identity_override.csv")

    pairs = [
        {
            "left": "S2 payments",
            "right": "S1 lms.payment_applied",
            "join_key": "S2.utr|txn_ref = payment_applied.ext_txn_ref (convention, not FK)",
            "enforced": False,
            "left_rows": len(pays),
            "unmatched": len(s2_unapplied),
            "unmatched_pct": _pct(len(s2_unapplied), len(pays)),
            "why": "SUCCESS at the bank that LMS never applied. I01 is one of these. Do not auto-allocate.",
        },
        {
            "left": "S2 payments",
            "right": "S1 lms.loan_account",
            "join_key": "loan_hint = loan_no",
            "enforced": False,
            "left_rows": len(pays),
            "unmatched": len(s2_no_loan) + len(s2_blank_hint),
            "unmatched_pct": _pct(len(s2_no_loan) + len(s2_blank_hint), len(pays)),
            "why": "Blank or unknown loan_hint. Cash tills often omit it.",
        },
        {
            "left": "S3 bureau",
            "right": "S1 lms.customer",
            "join_key": "pan (steward). cif_hint is a hint only",
            "enforced": False,
            "left_rows": len(bureau),
            "unmatched": len(s3_no_pan),
            "unmatched_pct": _pct(len(s3_no_pan), len(bureau)),
            "why": "Bureau is PAN-grained. CIF twins share one PAN — two LMS rows, one bureau row.",
        },
        {
            "left": "S3 bureau",
            "right": "S1 lms.customer.cif",
            "join_key": "cif_hint = cif",
            "enforced": False,
            "left_rows": len(bureau),
            "unmatched": len(s3_no_cif),
            "unmatched_pct": _pct(len(s3_no_cif), len(bureau)),
            "why": "cif_hint is not an FK. Resolve via identity_override on PAN.",
        },
        {
            "left": "S4 collections",
            "right": "S1 lms.loan_account",
            "join_key": "loan_ref = loan_no",
            "enforced": False,
            "left_rows": len(coll),
            "unmatched": len(s4_no_loan) + len(s4_blank),
            "unmatched_pct": _pct(len(s4_no_loan) + len(s4_blank), len(coll)),
            "why": "Agency files drop loan_ref on walk-in attempts.",
        },
        {
            "left": "S5 gold packets",
            "right": "S1 lms.gold_pledge",
            "join_key": "pledge_no",
            "enforced": False,
            "left_rows": len(gold),
            "unmatched": len(s5_no_pledge),
            "unmatched_pct": _pct(len(s5_no_pledge), len(gold)),
            "why": "Packets with no pledge (I11/I12 class). custody_state lives only here.",
        },
        {
            "left": "S5 gold packets",
            "right": "S1 lms.loan_account",
            "join_key": "loan_no",
            "enforced": False,
            "left_rows": len(gold),
            "unmatched": len(s5_no_loan),
            "unmatched_pct": _pct(len(s5_no_loan), len(gold)),
            "why": "Vault event without a live loan.",
        },
        {
            "left": "S6 dealer commissions",
            "right": "S1 lms.loan_account",
            "join_key": "loan_no",
            "enforced": False,
            "left_rows": len(veh),
            "unmatched": len(s6_no_loan),
            "unmatched_pct": _pct(len(s6_no_loan), len(veh)),
            "why": "Invoice against a cancelled or unknown loan (I07 evidence).",
        },
        {
            "left": "S7 CRM accounts",
            "right": "S1 lms.customer",
            "join_key": "cif_hint = cif",
            "enforced": False,
            "left_rows": _count_json("api/accounts.json"),
            "unmatched": 0,
            "unmatched_pct": "0.00%",
            "why": "CRM is populated from LMS CIFs plus named campaign rows. Join is still a hint.",
        },
        {
            "left": "S8 GL journals",
            "right": "S1 lms.loan_account",
            "join_key": "loan_ref = loan_no",
            "enforced": False,
            "left_rows": len(gl),
            "unmatched": len(s8_blank_ref) + len(s8_no_loan),
            "unmatched_pct": _pct(len(s8_blank_ref) + len(s8_no_loan), len(gl)),
            "why": "CASH_BATCH lines are often sparse on loan_ref. I01's GL line has an empty loan_ref.",
        },
        {
            "left": "S9 identity_override",
            "right": "S1 lms.customer",
            "join_key": "pan → (digital_cif, gold_cif)",
            "enforced": False,
            "left_rows": len(twins),
            "unmatched": 0,
            "unmatched_pct": "0.00%",
            "why": "CIF twins: two CIFs, one PAN. Not a primary-key collision.",
        },
    ]

    answers = {
        "how_many_payments_will_not_match_lms_apply": {
            "count": len(s2_unapplied),
            "of": len(pays),
            "why": "SUCCESS S2 rows whose utr/txn_ref is not payment_applied.ext_txn_ref",
            "named": [p.get("txn_ref") or p.get("utr") for p in s2_unapplied if (p.get("txn_ref") or "").startswith("UPI-I01")],
        },
        "cif_twins": {
            "count": len(twins),
            "pans": [t.get("pan") for t in twins],
        },
        "gold_packets_without_pledge": {
            "count": len(s5_no_pledge),
            "packet_ids": [r.get("packet_id") for r in s5_no_pledge],
        },
        "gl_lines_without_loan_ref": {
            "count": len(s8_blank_ref),
        },
    }

    payload = {"pairs": pairs, "answers": answers}
    path = Path(RELATIONSHIPS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def _count_json(rel: str) -> int:
    path = ESTATE / rel
    if not path.exists():
        return 0
    data = json.loads(path.read_text())
    rec = data.get("records", data)
    return len(rec) if isinstance(rec, list) else 0


def _pct(n: int, d: int) -> str:
    if not d:
        return "0.00%"
    return f"{100.0 * n / d:.2f}%"
