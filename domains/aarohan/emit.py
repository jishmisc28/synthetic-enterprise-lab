"""Write S1–S9. Caller replaces the output directory."""

from __future__ import annotations

import csv
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .constants import money
from .estate import Estate


def jsonable(obj):
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jsonable(v) for v in obj]
    if isinstance(obj, Decimal):
        return str(money(obj))
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def _csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = {}
            for k in fields:
                v = r.get(k)
                if isinstance(v, Decimal):
                    out[k] = str(money(v))
                elif isinstance(v, datetime):
                    out[k] = v.isoformat()
                elif isinstance(v, date):
                    out[k] = v.isoformat()
                elif k == "npa_flag" and v in (None, ""):
                    out[k] = "false"
                elif isinstance(v, bool):
                    out[k] = "true" if v else "false"
                elif v is None:
                    out[k] = ""
                else:
                    out[k] = v
            w.writerow(out)


def emit(e: Estate, out: Path) -> None:
    lms = out / "lms"
    lms.mkdir(parents=True)

    _csv(lms / "branch.csv", e.masters["branch_hierarchy"],
         ["branch_id", "branch_code", "branch_name", "state", "region",
          "gold_counter", "is_digital", "bm_email", "effective_to", "superseded_by"])
    _csv(lms / "product.csv", e.masters["product_catalog"],
         ["product_code", "name", "family", "annual_rate", "min_p", "max_p"])
    _csv(lms / "dealer.csv", e.masters["dealer_map"],
         ["dealer_code", "name", "city", "region"])
    _csv(lms / "agent.csv", e.masters["agent_hierarchy"],
         ["agent_code", "name", "region", "agency_code", "mgr_email",
          "effective_from", "effective_to", "home_branch"])
    _csv(lms / "customer.csv", e.customers,
         ["cif", "legal_name", "pan", "mobile", "branch_code", "dob"])
    _csv(lms / "kyc.csv", e.kyc,
         ["kyc_id", "cif", "pan", "aadhaar_last4", "status", "verified_at"])
    _csv(lms / "application.csv", e.applications,
         ["appl_no", "cif", "product_code", "applied_on", "amount"])
    _csv(lms / "bureau_pull.csv", e.bureau_pull,
         ["enquiry_ref", "appl_no", "cif", "score", "pulled_on"])
    _csv(lms / "credit_decision.csv", e.decisions,
         ["appl_no", "decided_on", "outcome", "score_used", "override_flag",
          "loan_no", "override_by"])
    _csv(lms / "loan_account.csv", e.loans,
         ["loan_no", "cif", "product_code", "branch_code", "principal",
          "outstanding_principal", "annual_rate", "tenor_m", "start_date",
          "status", "dpd", "npa_flag", "parent_loan_no", "dealer_code", "rm_id"])
    _csv(lms / "disbursement.csv", e.disbursements,
         ["disb_no", "loan_no", "amount", "disb_date", "seq", "is_topup"])
    _csv(lms / "repayment_schedule.csv", e.schedules,
         ["schedule_id", "loan_no", "version", "effective_from", "emi_amount", "tenor_m"])
    _csv(lms / "instalment.csv", e.instalments,
         ["instalment_id", "loan_no", "due_date", "amount", "status",
          "principal_due", "interest_due", "charge_due"])
    _csv(lms / "charge.csv", e.charges,
         ["charge_no", "loan_no", "reason", "amount", "event_date", "posted_at", "due_date"])
    _csv(lms / "waiver.csv", e.waivers,
         ["waiver_id", "charge_no", "amount", "posted_at"])
    _csv(lms / "payment_applied.csv", e.payments_applied,
         ["lms_receipt_no", "loan_no", "amount", "value_date", "posted_at", "ext_txn_ref"])
    _csv(lms / "payment_allocation.csv", e.allocations,
         ["lms_receipt_no", "seq", "component", "amount"])
    _csv(lms / "moratorium.csv", e.moratoriums,
         ["loan_no", "start_date", "end_date", "course_end", "grace_months"])
    _csv(lms / "restructure.csv", e.restructures,
         ["loan_no", "effective_from", "reason"])
    _csv(lms / "write_off.csv", e.write_offs,
         ["wo_no", "loan_no", "amount", "posted_date", "dpd_at", "approval_ref"])
    _csv(lms / "recovery.csv", e.recoveries,
         ["rec_no", "loan_no", "amount", "value_date", "reason"])
    # Vault custody lives in S5 — do not emit custody_state here.
    _csv(lms / "gold_pledge.csv", e.gold_pledge,
         ["pledge_no", "loan_no", "gross_g", "net_g", "purity", "assessed_inr"])
    _csv(lms / "vehicle_asset.csv", e.vehicle,
         ["loan_no", "vin", "dealer_code"])
    _csv(lms / "insurance_sale.csv", e.insurance,
         ["ins_id", "loan_no", "product", "premium", "sold_on"])
    rule_rows = []
    for r in e.rule_set:
        row = dict(r)
        payload = row.get("payload")
        if not isinstance(payload, str):
            row["payload"] = json.dumps(payload)
        rule_rows.append(row)
    _csv(lms / "rule_set.csv", rule_rows,
         ["rule_code", "product_code", "effective_from", "effective_to", "payload"])

    pay = out / "files" / "payments"
    by_ch = {"UPI": [], "NACH": [], "NEFT": [], "CASH": []}
    for r in e.s2:
        by_ch.setdefault(r.get("channel") or "UPI", []).append(r)
    fields = ["txn_ref", "utr", "channel", "status", "amount", "event_date",
              "value_date", "settlement_date", "ingested_at", "loan_hint", "mandate_id"]
    for ch, rows in by_ch.items():
        _csv(pay / f"{ch.lower()}.csv", rows, fields)

    _csv(out / "files" / "bureau" / "bureau_2026-07.csv", e.s3,
         ["bureau_id", "pan", "score", "reported_as_of", "enquiry_ref", "cif_hint",
          "active_tradelines", "enquiries_90d", "worst_dpd_24m", "reported_outstanding"])
    _csv(out / "files" / "collections" / "events.csv", e.s4,
         ["event_id", "loan_ref", "agent_code", "kind", "event_date", "amount"])
    _csv(out / "files" / "collections" / "incentives.csv", e.incentives,
         ["incentive_id", "agent_code", "loan_no", "amount", "paid_date", "recovery_value_date"])
    _csv(out / "files" / "gold" / "packets.csv", e.s5,
         ["packet_id", "pledge_no", "loan_no", "kind", "valuation_date", "event_date",
          "gross_g", "net_g", "purity", "assessed_inr", "custody_state", "principal",
          "proceeds_inr"])
    _csv(out / "files" / "vehicle" / "commissions.csv", e.s6,
         ["commission_id", "loan_no", "dealer_code", "vin", "invoice_no",
          "amount", "paid_date", "disb_no"])
    _csv(out / "files" / "gl" / "journals.csv", e.s8,
         ["je_id", "posted_date", "account_code", "amount", "loan_ref", "source"])

    api = out / "api"
    api.mkdir(parents=True)
    (api / "accounts.json").write_text(
        json.dumps({"records": jsonable(e.s7)}, indent=2) + "\n", encoding="utf-8")
    (api / "campaigns.json").write_text(
        json.dumps({"records": jsonable(e.campaigns)}, indent=2) + "\n", encoding="utf-8")

    masters = out / "files" / "masters"
    for name, rows in e.masters.items():
        if name == "rule_set":
            continue
        if not rows:
            continue
        keys: list[str] = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        _csv(masters / f"{name}.csv", rows, keys)
    _csv(masters / "identity_override.csv", e.identity_override,
         ["pan", "digital_cif", "gold_cif", "name_lms", "name_gold", "name_bureau"])
    (masters / "rule_set.json").write_text(
        json.dumps(jsonable(e.rule_set), indent=2) + "\n", encoding="utf-8")

    (out / "ground_truth.json").write_text(
        json.dumps(jsonable(e.ground_truth), indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    _assert_unique(e)


def _assert_unique(e: Estate) -> None:
    """Fail generate if a typed PK would collide. CIF twins are two CIFs, one PAN."""
    def uniq(rows, key, label):
        seen = set()
        dups = []
        for r in rows:
            k = r.get(key)
            if k in seen:
                dups.append(k)
            seen.add(k)
        if dups:
            raise SystemExit(f"duplicate {label}: {dups[:8]}")

    uniq(e.customers, "cif", "lms.customer.cif")
    uniq(e.kyc, "kyc_id", "lms.kyc.kyc_id")
    uniq(e.masters.get("dealer_map", []), "dealer_code", "lms.dealer.dealer_code")
    uniq(e.loans, "loan_no", "lms.loan_account.loan_no")
    agents = e.masters.get("agent_hierarchy", [])
    seen_ag = set()
    for a in agents:
        k = (a.get("agent_code"), a.get("effective_from"))
        if k in seen_ag:
            raise SystemExit(f"duplicate lms.agent {k}")
        seen_ag.add(k)
