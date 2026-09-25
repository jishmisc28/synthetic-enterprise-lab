"""Monitor predicates and KPIs. Money is Decimal. Do not copy the manifest blindly."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from .constants import CLAWBACK_DAYS, CLOSE_DATE, GOLD_REVAL_DAYS, WRITEOFF_DPD, WRITEOFF_RESIDUAL, money
from .estate import Estate
from .rules import gold_ltv_limit, grace_days, score_cutoff, waterfall_order


def _d(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date) and not isinstance(v, type(CLOSE_DATE)):
        return v
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _dec(v) -> Decimal:
    if v is None or v == "":
        return money(0)
    return money(v)


def _loan_map(e: Estate) -> dict[str, dict]:
    return {ln["loan_no"]: ln for ln in e.loans}


def _max_dpd_for_cif(e: Estate, cif: str) -> int:
    return max((int(ln.get("dpd") or 0) for ln in e.loans if ln["cif"] == cif), default=0)


def evaluate_monitors(e: Estate) -> dict:
    loans = _loan_map(e)
    applied_refs = {p.get("ext_txn_ref") for p in e.payments_applied if p.get("ext_txn_ref")}
    overdue_loans = {
        ins["loan_no"]
        for ins in e.instalments
        if ins.get("status") == "OVERDUE"
    }

    # M1 — bank SUCCESS, no LMS apply, instalment still overdue
    m1 = []
    for p in e.s2:
        if p.get("status") != "SUCCESS":
            continue
        vd = _d(p.get("value_date"))
        if not vd or vd > CLOSE_DATE:
            continue
        refs = {p.get("utr"), p.get("txn_ref")}
        if refs & applied_refs:
            continue
        hint = p.get("loan_hint")
        if hint in overdue_loans:
            m1.append(hint)

    # M2 — late charge inside grace, or EDU EMI inside moratorium
    m2 = []
    moras = {m["loan_no"]: m for m in e.moratoriums}
    pays_by_loan = defaultdict(list)
    for p in e.payments_applied:
        pays_by_loan[p["loan_no"]].append(p)
    for ch in e.charges:
        if ch.get("reason") != "LATE":
            continue
        ln = loans.get(ch["loan_no"])
        if not ln:
            continue
        due = _d(ch.get("due_date"))
        paid = None
        for p in pays_by_loan.get(ch["loan_no"], []):
            pv = _d(p.get("value_date"))
            if due and pv and abs((pv - due).days) <= 14:
                paid = pv
                break
        event = _d(ch.get("event_date"))
        when = paid or event
        if due and when:
            grace = grace_days(ln["product_code"], when)
            if (when - due).days <= grace:
                m2.append(ch["charge_no"])
    for ins in e.instalments:
        mora = moras.get(ins["loan_no"])
        if not mora:
            continue
        due = _d(ins["due_date"])
        end = _d(mora["end_date"])
        if due and end and due < end:
            m2.append(ins["instalment_id"])

    # M3 — charges-first after waterfall v2 while interest remains
    m3 = []
    first_alloc = {}
    for a in e.allocations:
        rec = first_alloc.get(a["lms_receipt_no"])
        if rec is None or int(a["seq"]) < int(rec["seq"]):
            first_alloc[a["lms_receipt_no"]] = a
    inst_int = defaultdict(lambda: money(0))
    for ins in e.instalments:
        inst_int[ins["loan_no"]] += _dec(ins.get("interest_due"))
    for p in e.payments_applied:
        vd = _d(p["value_date"])
        ln = loans.get(p["loan_no"])
        if not ln or not vd:
            continue
        if ln["product_code"] not in {"PL", "BNPL", "EDU"}:
            continue
        if vd < date(2025, 4, 1):
            continue
        first = first_alloc.get(p["lms_receipt_no"])
        if not first:
            continue
        order = waterfall_order(ln["product_code"], vd)
        if first["component"] == "CHARGE" and order[0] != "CHARGE" and inst_int[p["loan_no"]] > 0:
            m3.append(p["lms_receipt_no"])

    # M4 — ≥3 attempts in 14d, DPD≥30, no PTP_KEPT, no S2 success
    m4 = []
    s2_ok = defaultdict(list)
    for p in e.s2:
        if p.get("status") == "SUCCESS" and p.get("loan_hint"):
            s2_ok[p["loan_hint"]].append(_d(p.get("value_date")))
    by_loan_ev = defaultdict(list)
    for ev in e.s4:
        by_loan_ev[ev["loan_ref"]].append(ev)
    window_start = CLOSE_DATE - timedelta(days=14)
    for loan_no, evs in by_loan_ev.items():
        ln = loans.get(loan_no)
        if not ln or int(ln.get("dpd") or 0) < 30:
            continue
        recent = [ev for ev in evs if _d(ev.get("event_date")) and _d(ev["event_date"]) >= window_start]
        if len(recent) < 3:
            continue
        if any(ev.get("kind") == "PTP_KEPT" for ev in recent):
            continue
        if any(vd and window_start <= vd <= CLOSE_DATE for vd in s2_ok.get(loan_no, [])):
            continue
        m4.append(loan_no)

    # M5 — clawback window reversal, or wrong agent
    m5 = []
    reversals = [
        p for p in e.s2
        if p.get("status") == "REVERSED"
    ]
    recoveries_s4 = [ev for ev in e.s4 if ev.get("kind") == "RECOVERY"]
    for inc in e.incentives:
        rvd = _d(inc.get("recovery_value_date"))
        clawed = False
        for rev in reversals:
            if rev.get("loan_hint") != inc["loan_no"]:
                continue
            rd = _d(rev.get("value_date"))
            if rvd and rd and 0 <= (rd - rvd).days <= CLAWBACK_DAYS:
                clawed = True
        collectors = {
            ev["agent_code"] for ev in recoveries_s4
            if ev.get("loan_ref") == inc["loan_no"]
        }
        wrong_agent = bool(collectors) and inc["agent_code"] not in collectors
        if clawed or wrong_agent:
            m5.append(inc["incentive_id"])

    # M6 — below cutoff without override, or sibling DPD ≥ 60
    m6 = []
    for dec in e.decisions:
        if dec.get("outcome") != "APPROVED":
            continue
        app = next((a for a in e.applications if a["appl_no"] == dec["appl_no"]), None)
        if not app:
            continue
        on = _d(dec["decided_on"])
        cutoff = score_cutoff(app["product_code"], on) if on else 0
        score = int(dec.get("score_used") or 0)
        override = dec.get("override_flag") in (True, "true", "True")
        if score < cutoff and not override:
            m6.append(dec["appl_no"])
            continue
        cif = app["cif"]
        new_loan = dec.get("loan_no")
        siblings = [
            ln for ln in e.loans
            if ln["cif"] == cif and ln["loan_no"] != new_loan
            and ln.get("status") not in {"CLOSED", "SETTLED", "WRITTEN_OFF"}
            and int(ln.get("dpd") or 0) >= 60
        ]
        if siblings and app["product_code"] in {"PL", "BNPL"}:
            m6.append(dec["appl_no"])

    # M7 — LTV / release / stale valuation
    m7 = []
    for g in e.s5:
        ln = loans.get(g["loan_no"])
        if not ln:
            continue
        packet = g.get("packet_id") or g.get("pledge_no")
        val = _d(g.get("valuation_date"))
        assessed = _dec(g.get("assessed_inr"))
        prin = _dec(g.get("principal")) or _dec(ln.get("principal"))
        status = ln.get("status")
        custody = g.get("custody_state")
        if custody == "RELEASED" and status not in {"CLOSED", "SETTLED"}:
            m7.append(packet)
            continue
        if val and assessed > 0 and status not in {"CLOSED", "SETTLED"}:
            ltv = prin / assessed
            if ltv > gold_ltv_limit(val):
                m7.append(packet)
                continue
        if val and status == "ACTIVE" and (CLOSE_DATE - val).days > GOLD_REVAL_DAYS:
            m7.append(packet)

    # M8 — unsupported WO / misposted recovery / auction break
    m8 = []
    wo_by_loan = {w["loan_no"]: w for w in e.write_offs}
    for w in e.write_offs:
        amt = _dec(w["amount"])
        dpd_at = int(w.get("dpd_at") or 0)
        appr = w.get("approval_ref") or ""
        if dpd_at < WRITEOFF_DPD and amt > WRITEOFF_RESIDUAL and not appr:
            m8.append(w["wo_no"])
    for rec in e.recoveries:
        if rec.get("reason") == "POST_WO":
            if rec["loan_no"] not in wo_by_loan:
                m8.append(rec["rec_no"])
        if rec.get("reason") == "AUCTION":
            auc = next((g for g in e.s5 if g.get("loan_no") == rec["loan_no"] and g.get("kind") == "AUCTION"), None)
            if auc and _dec(auc.get("proceeds_inr")) != _dec(rec["amount"]):
                m8.append(auc.get("packet_id") or rec["rec_no"])

    # M9 — unsecured offer to stressed CIF
    m9 = []
    for camp in e.campaigns:
        if camp.get("product_code") not in {"PL", "BNPL"}:
            continue
        if _max_dpd_for_cif(e, camp["cif"]) >= 30:
            m9.append(camp["offer_id"])

    # M10 — S2 vs LMS vs GL; plus dealer-commission cousin I07
    m10 = []
    timing = []
    s2_by = defaultdict(lambda: money(0))
    lms_by = defaultdict(lambda: money(0))
    gl_by = defaultdict(lambda: money(0))
    for p in e.s2:
        hint = p.get("loan_hint")
        vd = _d(p.get("value_date"))
        if not hint or not vd or vd > CLOSE_DATE:
            continue
        if p.get("status") == "SUCCESS":
            s2_by[(hint, vd)] += _dec(p["amount"])
        elif p.get("status") == "REVERSED":
            # pair against the original value_date when present on the SUCCESS twin
            orig = next((q for q in e.s2 if q.get("utr") and q.get("utr") == p.get("utr")
                         and q.get("status") == "SUCCESS"), None)
            orig_vd = _d(orig.get("value_date")) if orig else vd
            if orig_vd and orig_vd <= CLOSE_DATE:
                s2_by[(hint, orig_vd)] -= _dec(p["amount"])
    for p in e.payments_applied:
        vd = _d(p.get("value_date"))
        if vd and vd <= CLOSE_DATE:
            lms_by[(p["loan_no"], vd)] += _dec(p["amount"])
    for g in e.s8:
        if g.get("account_code") in {"CASH_BATCH", "LOAN-CONTROL"} and g.get("loan_ref"):
            pd = _d(g.get("posted_date"))
            if pd:
                gl_by[(g["loan_ref"], pd - timedelta(days=1))] += _dec(g["amount"])
    keys = set(s2_by) | set(lms_by) | set(gl_by)
    for key in keys:
        s2v, lmsv, glv = s2_by[key], lms_by[key], gl_by[key]
        if abs(s2v - lmsv) > Decimal("0.0001"):
            m10.append(key[0])
        elif abs(glv - lmsv) > Decimal("0.0001") and glv > 0 and lmsv > 0:
            # same-day vs T+1 already shifted; residual here is a real break
            m10.append(key[0])
        elif abs(glv - lmsv) > Decimal("0.0001") and (glv == 0 or lmsv == 0):
            # structural timing listed separately when the other two books tie
            if abs(s2v - lmsv) <= Decimal("0.0001"):
                timing.append(f"{key[1].isoformat()}|{key[0]}")
    # I13 auction vs GL
    for g in e.s5:
        if g.get("kind") != "AUCTION":
            continue
        rec = next((r for r in e.recoveries if r["loan_no"] == g["loan_no"]), None)
        if rec and _dec(g.get("proceeds_inr")) != _dec(rec["amount"]):
            m10.append(g["loan_no"])
    # I07 duplicate first disbursement with commission
    disb_by = defaultdict(list)
    for d in e.disbursements:
        if not d.get("is_topup"):
            disb_by[d["loan_no"]].append(d)
    comm_loans = {c["loan_no"] for c in e.s6}
    for loan_no, ds in disb_by.items():
        if len(ds) >= 2 and loan_no in comm_loans:
            amts = [_dec(x["amount"]) for x in ds]
            dates = [_d(x["disb_date"]) for x in ds]
            if len(set(amts)) == 1 and len(set(dates)) == 1:
                m10.append(loan_no)

    def _uniq(xs):
        out = []
        for x in xs:
            if x not in out:
                out.append(x)
        return out

    return {
        "M1": {"must": ["AF-LN-I01-PL"], "must_not": ["AF-LN-I01N-PL"],
               "observed": _uniq(m1), "count": len(_uniq(m1)),
               "owner": "finance.controller@aarohan.example"},
        "M2": {"must": ["CHG-I03", "INS-I04"], "must_not": ["CHG-I03N"],
               "observed": _uniq(m2), "count": len(_uniq(m2)),
               "owner": "product.pl@aarohan.example"},
        "M3": {"must": ["RCPT-I02"], "must_not": ["RCPT-I02N"],
               "observed": _uniq(m3), "count": len(_uniq(m3)),
               "owner": "finance.controller@aarohan.example"},
        "M4": {"must": ["AF-LN-M4-EMPTY"], "must_not": ["AF-LN-M4-ZERO"],
               "observed": _uniq(m4), "count": len(_uniq(m4)),
               "owner": "collections.mgr.digital@aarohan.example"},
        "M5": {"must": ["INC-I05", "INC-I06"], "must_not": ["INC-I05N"],
               "observed": _uniq(m5), "count": len(_uniq(m5)),
               "owner": "collections.mgr.west@aarohan.example"},
        "M6": {"must": ["AF-AP-I08", "AF-AP-I09"], "must_not": ["AF-AP-I08N"],
               "observed": _uniq(m6), "count": len(_uniq(m6)),
               "owner": "credit.mgr@aarohan.example"},
        "M7": {"must": ["PKT-I10", "PKT-I11", "PKT-I12"], "must_not": ["PKT-I10N"],
               "observed": _uniq(m7), "count": len(_uniq(m7)),
               "owner": "gold.ops.pnq-kth@aarohan.example"},
        "M8": {"must": ["PKT-I13", "WO-I14", "REC-I15"], "must_not": ["WO-I14N"],
               "observed": _uniq(m8), "count": len(_uniq(m8)),
               "owner": "finance.controller@aarohan.example"},
        "M9": {"must": ["CMP-I09"], "must_not": ["CMP-GOLD-OK"],
               "observed": _uniq(m9), "count": len(_uniq(m9)),
               "owner": "product.crm@aarohan.example"},
        "M10": {"must": ["AF-LN-I01-PL", "AF-LN-I13-GL", "AF-LN-I07-TW"],
                "must_not": ["timing_not_break"],
                "observed": _uniq(m10), "count": len(_uniq(m10)),
                "timing_not_break": _uniq(timing),
                "owner": "finance.controller@aarohan.example"},
    }


def evaluate_kpis(e: Estate, monitors: dict) -> dict:
    period_start = date(2026, 8, 1)
    disb = sum((_dec(d["amount"]) for d in e.disbursements
                if _d(d.get("disb_date")) and period_start <= _d(d["disb_date"]) <= CLOSE_DATE),
               Decimal("0"))
    live = [ln for ln in e.loans if ln.get("status") in {"ACTIVE", "NPA"} or (
        ln.get("status") not in {"CLOSED", "SETTLED", "WRITTEN_OFF"}
    )]
    aum = money(sum((_dec(ln.get("outstanding_principal") or ln.get("principal"))
                     for ln in live), Decimal("0")))
    aum_90 = money(sum((_dec(ln.get("outstanding_principal") or ln.get("principal"))
                        for ln in live if int(ln.get("dpd") or 0) >= 90), Decimal("0")))
    aum_npa = money(sum((_dec(ln.get("outstanding_principal") or ln.get("principal"))
                         for ln in live if ln.get("npa_flag") or int(ln.get("dpd") or 0) >= 90),
                        Decimal("0")))
    interest = money(sum((_dec(a["amount"]) for a in e.allocations if a.get("component") == "INTEREST"),
                         Decimal("0")))
    fees = money(sum((_dec(c["amount"]) for c in e.charges), Decimal("0")))
    k4 = money(sum((_dec(c["amount"]) for c in e.charges if c.get("charge_no") in monitors["M2"]["observed"]),
                   Decimal("0")))
    due_amt = money(sum((_dec(i["amount"]) for i in e.instalments
                         if _d(i.get("due_date")) and period_start <= _d(i["due_date"]) <= CLOSE_DATE),
                        Decimal("0")))
    s2_period = money(sum((_dec(p["amount"]) for p in e.s2
                           if p.get("status") == "SUCCESS"
                           and _d(p.get("value_date"))
                           and period_start <= _d(p["value_date"]) <= CLOSE_DATE),
                          Decimal("0")))
    k5 = (s2_period / due_amt) if due_amt else Decimal("0")
    wo_period = money(sum((_dec(w["amount"]) for w in e.write_offs
                           if _d(w.get("posted_date")) and period_start <= _d(w["posted_date"]) <= CLOSE_DATE),
                          Decimal("0")))
    wo_stock = money(sum((_dec(w["amount"]) for w in e.write_offs), Decimal("0")))
    rec_amt = money(sum((_dec(r["amount"]) for r in e.recoveries
                         if _d(r.get("value_date")) and r["value_date"] and
                         _d(r["value_date"]) <= CLOSE_DATE), Decimal("0")))
    k10 = (rec_amt / wo_stock) if wo_stock else Decimal("0")
    k12 = sum(1 for x in monitors["M7"]["observed"] if x == "PKT-I10") + (
        1 if "PKT-I10" in monitors["M7"]["observed"] else 0
    )
    # K12 is live LTV-breach count (I10), not release/stale
    k12 = 1 if "PKT-I10" in monitors["M7"]["observed"] else 0
    k13 = len([x for x in monitors["M10"]["observed"] if x != "timing_not_break"])
    ptp_made = sum(1 for ev in e.s4 if ev.get("kind") == "PTP_MADE")
    ptp_kept = sum(1 for ev in e.s4 if ev.get("kind") == "PTP_KEPT")
    k14 = (Decimal(ptp_kept) / Decimal(ptp_made)) if ptp_made else Decimal("0")

    by_prod = defaultdict(lambda: {"interest": Decimal("0"), "fees": Decimal("0"),
                                   "comm": Decimal("0"), "inc": Decimal("0"),
                                   "wo": Decimal("0"), "rec": Decimal("0")})
    loan_prod = {ln["loan_no"]: ln["product_code"] for ln in e.loans}
    receipt_loan = {p["lms_receipt_no"]: p["loan_no"] for p in e.payments_applied}
    for a in e.allocations:
        if a.get("component") == "INTEREST":
            by_prod[loan_prod.get(receipt_loan.get(a["lms_receipt_no"], "UNK"))]["interest"] += _dec(a["amount"])
    for c in e.charges:
        by_prod[loan_prod.get(c["loan_no"], c.get("loan_no"))]["fees"] += _dec(c["amount"])
    for c in e.s6:
        by_prod[loan_prod.get(c["loan_no"], "TW")]["comm"] += _dec(c["amount"])
    for inc in e.incentives:
        by_prod[loan_prod.get(inc["loan_no"], "PL")]["inc"] += _dec(inc["amount"])
    for w in e.write_offs:
        by_prod[loan_prod.get(w["loan_no"], "PL")]["wo"] += _dec(w["amount"])
    for r in e.recoveries:
        by_prod[loan_prod.get(r["loan_no"], "PL")]["rec"] += _dec(r["amount"])
    k11 = []
    for prod, b in sorted(by_prod.items()):
        if prod in (None, "UNK"):
            continue
        contrib = money(b["interest"] + b["fees"] - b["comm"] - b["inc"] - b["wo"] + b["rec"])
        k11.append({"product_code": prod, "contribution": str(contrib)})

    def am(id_, unit, value, num=None, den=None):
        if isinstance(value, Decimal):
            sval = str(money(value)) if unit in {"inr", "count"} else f"{float(value):.4f}"
        else:
            sval = f"{float(value):.4f}" if unit == "rate" else str(value)
        if unit == "rate" and isinstance(value, Decimal):
            sval = f"{float(value):.4f}"
        if unit == "inr":
            sval = str(money(value))
        return {"id": id_, "shape": "AM", "as_at": "close", "value": sval, "unit": unit,
                "numerator": num if num is None or isinstance(num, int) else str(num),
                "denominator": den if den is None or isinstance(den, int) else str(den)}

    return {
        "K1": am("K1", "inr", money(disb)),
        "K2": am("K2", "inr", aum),
        "K3": am("K3", "inr", money(interest + fees)),
        "K4": am("K4", "inr", k4),
        "K5": am("K5", "rate", k5),
        "K6": am("K6", "rate", (aum_90 / aum) if aum else Decimal("0")),
        "K7": {"id": "K7", "shape": "DM", "note": "roll 0→1 requires a prior-month snapshot; tiny emits the named book only",
               "row_count": 0},
        "K8": am("K8", "rate", (aum_npa / aum) if aum else Decimal("0")),
        "K9": am("K9", "inr", wo_period),
        "K10": am("K10", "rate", k10),
        "K11": {"id": "K11", "shape": "DM", "rows": k11, "row_count": len(k11)},
        "K12": am("K12", "count", Decimal(k12), k12, None),
        "K13": am("K13", "count", Decimal(k13), k13, None),
        "K14": am("K14", "rate", k14, ptp_kept, ptp_made),
    }


def evaluate(e: Estate) -> dict:
    monitors = evaluate_monitors(e)
    kpis = evaluate_kpis(e, monitors)
    valid = [g for g in e.ground_truth if g.get("kind") == "valid"]
    near = [g for g in e.ground_truth if g.get("kind") == "near_miss"]
    return {
        "seed": e.seed,
        "scale": e.scale,
        "estate": "aarohan",
        "close_date": CLOSE_DATE.isoformat(),
        "kpis": kpis,
        "monitors": monitors,
        "incidents": {
            "valid": [g["incident_id"] for g in valid],
            "near_miss": [g["incident_id"] for g in near],
            "count_valid": len(valid),
            "count_near_miss": len(near),
        },
        "cleaning": {
            "customers": len(e.customers),
            "loans": len(e.loans),
            "instalments": len(e.instalments),
            "s2_payments": len(e.s2),
            "collection_events": len(e.s4),
            "gold_ops": len(e.s5),
            "gl_lines": len(e.s8),
            "identity_twins": len(e.identity_override),
        },
    }


def write_verification_md(data: dict) -> str:
    lines = [
        f"# Verification sheet (generated, estate=aarohan, scale={data['scale']}, seed={data['seed']})",
        "",
        f"Close: {data['close_date']}",
        "",
        "## KPIs",
        "",
        "| ID | Value | Unit |",
        "|---|---|---|",
    ]
    for kid, k in data["kpis"].items():
        if k.get("shape") == "AM":
            lines.append(f"| {kid} | {k['value']} | {k['unit']} |")
        else:
            lines.append(f"| {kid} | rows={k.get('row_count', '?')} | DM |")
    lines += ["", "## Monitors", ""]
    for mid, m in data["monitors"].items():
        lines.append(f"- **{mid}** observed {m['count']}: `{m['observed']}` (must {m['must']}; must not {m['must_not']})")
    lines += [
        "",
        "## Incidents",
        "",
        f"Valid: {data['incidents']['valid']}",
        f"Near-miss: {data['incidents']['near_miss']}",
        "",
        "## Cleaning",
        "",
        json.dumps(data["cleaning"], indent=2),
        "",
    ]
    return "\n".join(lines) + "\n"


def sha256_file(path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()
