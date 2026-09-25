"""Assemble the Aarohan estate: named incidents + scale-dependent background.

Background loans are deliberately clean against every monitor predicate.
Named keys do not change with scale.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from .catalogs import PRODUCTS, agents, branches, dealers, person
from .constants import CLOSE_DATE, GOLD_REVAL_DAYS, SCALES, WINDOW_START, money
from .identity import TWINS
from .incidents import seed_incidents
from .money import allocate, emi
from .rules import RULES, gold_ltv_limit, waterfall_order


def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    month = m % 12 + 1
    return date(y, month, min(d.day, 28))


def _product(code: str) -> dict:
    return next(p for p in PRODUCTS if p["product_code"] == code)


@dataclass
class Estate:
    scale: str
    seed: int
    customers: list[dict] = field(default_factory=list)
    applications: list[dict] = field(default_factory=list)
    kyc: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    bureau_pull: list[dict] = field(default_factory=list)
    loans: list[dict] = field(default_factory=list)
    disbursements: list[dict] = field(default_factory=list)
    schedules: list[dict] = field(default_factory=list)
    instalments: list[dict] = field(default_factory=list)
    charges: list[dict] = field(default_factory=list)
    waivers: list[dict] = field(default_factory=list)
    payments_applied: list[dict] = field(default_factory=list)
    allocations: list[dict] = field(default_factory=list)
    moratoriums: list[dict] = field(default_factory=list)
    restructures: list[dict] = field(default_factory=list)
    write_offs: list[dict] = field(default_factory=list)
    recoveries: list[dict] = field(default_factory=list)
    gold_pledge: list[dict] = field(default_factory=list)
    vehicle: list[dict] = field(default_factory=list)
    insurance: list[dict] = field(default_factory=list)
    s2: list[dict] = field(default_factory=list)
    s3: list[dict] = field(default_factory=list)
    s4: list[dict] = field(default_factory=list)
    s5: list[dict] = field(default_factory=list)
    s6: list[dict] = field(default_factory=list)
    s7: list[dict] = field(default_factory=list)
    s8: list[dict] = field(default_factory=list)
    incentives: list[dict] = field(default_factory=list)
    campaigns: list[dict] = field(default_factory=list)
    ground_truth: list[dict] = field(default_factory=list)
    rule_set: list[dict] = field(default_factory=list)
    masters: dict[str, list[dict]] = field(default_factory=dict)
    identity_override: list[dict] = field(default_factory=list)


def _extend(e: Estate, src: dict[str, Any]) -> None:
    rename = {}
    for k, v in src.items():
        attr = rename.get(k, k)
        if attr == "ground_truth":
            e.ground_truth.extend(v)
            continue
        bucket = getattr(e, attr, None)
        if isinstance(bucket, list):
            bucket.extend(v)


def _masters() -> dict[str, list[dict]]:
    br = branches()
    # Stale rename: Pune Kothrud also listed under a retired code
    stale = [{
        "branch_id": 99, "branch_code": "PNQ-KTH-OLD", "branch_name": "Pune Kothrud (legacy)",
        "state": "MH", "region": "WEST", "gold_counter": True, "is_digital": False,
        "bm_email": "bm.pnq-kth@aarohan.example",
        "effective_to": "2025-03-31", "superseded_by": "PNQ-KTH",
    }]
    return {
        "branch_hierarchy": br + stale,
        "agent_hierarchy": agents(),
        "dealer_map": dealers(),
        "product_catalog": list(PRODUCTS),
        "rule_set": list(RULES),
    }


def _kyc_for(cust: dict, when: str = "2024-10-01") -> dict:
    return {
        "kyc_id": f"KYC-{cust['cif']}",
        "cif": cust["cif"],
        "pan": cust["pan"],
        "aadhaar_last4": "4321",
        "status": "verified",
        "verified_at": when,
    }


def _bg_customer(i: int) -> dict:
    br = branches()[i % len(branches())]
    name, pan, mobile = person(i + 5000)
    return {
        "cif": f"AF-{10_000_000 + i:08d}",
        "legal_name": name,
        "pan": pan,
        "mobile": mobile,
        "branch_code": br["branch_code"],
        "dob": "1990-01-15",
    }


def _pick_product(i: int) -> str:
    pick = i % 100
    # BNPL heavy, then PL, then gold / vehicle / edu
    if pick < 38:
        return "BNPL"
    if pick < 70:
        return "PL"
    if pick < 82:
        return "GOLD"
    if pick < 90:
        return "TW"
    if pick < 95:
        return "UV"
    return "EDU"


def _principal(code: str, i: int) -> Decimal:
    if i % 19 == 0 and code in {"BNPL", "PL"}:
        return money(3500)  # micro ticket
    base = {
        "PL": money(175000),
        "BNPL": money(9000),
        "TW": money(88000),
        "UV": money(245000),
        "EDU": money(480000),
        "GOLD": money(185000),
    }[code]
    return money(base + money(500) * (i % 17))


def _bg_loan(i: int, cust: dict, pay_depth: int = 8) -> dict[str, list]:
    code = _pick_product(i)
    prod = _product(code)
    brs = branches()
    br = brs[i % len(brs)]
    if code == "GOLD":
        gold_br = [b for b in brs if b["gold_counter"]]
        br = gold_br[i % len(gold_br)]
    if code == "BNPL" and i % 3 == 0:
        br = next(b for b in brs if b["is_digital"])
    prin = _principal(code, i)
    tenor = prod["tenors"][i % len(prod["tenors"])]
    rate = Decimal(prod["annual_rate"])
    origin = WINDOW_START + timedelta(days=3 + (i % 520))
    if origin > date(2026, 5, 15):
        origin = date(2025, 11, 10) + timedelta(days=i % 40)
    if i % 11 == 0:
        origin = date(2026, 8, 1) + timedelta(days=i % 25)
        if origin > CLOSE_DATE:
            origin = date(2026, 8, 18)
    lid = f"AF-LN-BG-{i:06d}-{code}"
    status = "ACTIVE"
    dpd = 0
    if i % 47 == 0:
        dpd = 16
    elif i % 61 == 0:
        dpd = 42
        # keep collection thin so M4 does not fire
    elif i % 89 == 0:
        dpd = 95
        status = "ACTIVE"
    e = emi(prin, rate, tenor)
    live = status not in {"CLOSED", "SETTLED", "WRITTEN_OFF"}
    outstanding = prin if live else money(0)
    if dpd >= 90:
        outstanding = money(prin * Decimal("0.62"))
    loan = {
        "loan_no": lid,
        "cif": cust["cif"],
        "product_code": code,
        "branch_code": br["branch_code"],
        "principal": prin,
        "outstanding_principal": outstanding,
        "annual_rate": rate,
        "tenor_m": tenor,
        "start_date": origin,
        "status": status,
        "dpd": dpd,
        "npa_flag": dpd >= 90,
        "parent_loan_no": None,
        "dealer_code": dealers()[i % len(dealers())]["dealer_code"] if code in {"TW", "UV"} else None,
        "rm_id": f"RM-{(i % 12) + 1:02d}",
    }
    n_emit = min(tenor, pay_depth)
    n_paid = 3 if dpd == 0 else (1 if dpd < 90 else 0)
    insts, pays, allocs, s2, gl = [], [], [], [], []
    for n in range(1, n_emit + 1):
        due = add_months(origin, n)
        if due > CLOSE_DATE:
            break
        if n <= n_paid:
            st = "PAID"
        elif dpd > 0:
            st = "OVERDUE"
        else:
            st = "DUE"
        insts.append({
            "instalment_id": f"{lid}-I{n:02d}",
            "loan_no": lid,
            "due_date": due,
            "amount": e,
            "status": st,
            "principal_due": money(e * Decimal("0.72")),
            "interest_due": money(e * Decimal("0.28")),
            "charge_due": money(0),
        })
        if st == "PAID":
            pid = f"RCPT-BG-{i:06d}-{n:02d}"
            channel = "CASH" if code == "GOLD" else ("UPI" if code == "BNPL" else "NACH")
            utr = f"NACHBG{i:06d}{n:02d}" if channel != "CASH" else ""
            pays.append({
                "lms_receipt_no": pid,
                "loan_no": lid,
                "amount": e,
                "value_date": due,
                "posted_at": f"{due}T10:15:00+05:30",
                "ext_txn_ref": utr or f"CASH-BG-{i:06d}-{n:02d}",
            })
            order = waterfall_order(code, due)
            split = allocate(e, money(0), money(e * Decimal("0.28")), money(e * Decimal("0.72")), order)
            for seq, comp in enumerate(order, 1):
                allocs.append({
                    "lms_receipt_no": pid, "seq": seq, "component": comp, "amount": split[comp],
                })
            s2.append({
                "txn_ref": f"{channel}-BG-{i:06d}-{n:02d}",
                "utr": utr,
                "channel": channel,
                "status": "SUCCESS",
                "amount": e,
                "event_date": due,
                "value_date": due,
                "settlement_date": due if channel == "CASH" else due + timedelta(days=1 if channel == "NACH" else 0),
                "ingested_at": f"{due}T10:00:00+05:30",
                "loan_hint": lid,
                "mandate_id": f"MND-BG-{i:06d}" if channel == "NACH" else "",
            })
            if i % 33 == 0 and n == 1 and channel == "UPI":
                s2.append({
                    "txn_ref": f"{channel}-BG-{i:06d}-{n:02d}-DUP",
                    "utr": utr,
                    "channel": channel,
                    "status": "CREATED",
                    "amount": e,
                    "event_date": due,
                    "value_date": due,
                    "settlement_date": due,
                    "ingested_at": f"{due}T10:00:08+05:30",
                    "loan_hint": lid,
                    "mandate_id": "",
                })
            gl.append({
                "je_id": f"JE-BG-{i:06d}-{n:02d}",
                "posted_date": due + timedelta(days=1),
                "account_code": "CASH_BATCH",
                "amount": e,
                "loan_ref": lid,
                "source": "CASH_BATCH",
            })
    gold, gold_ops, veh, s6, ins = [], [], [], [], []
    if code == "GOLD":
        # Keep valuations inside policy so M7 does not fire on background
        val_date = max(origin, CLOSE_DATE - timedelta(days=GOLD_REVAL_DAYS - 20))
        limit = gold_ltv_limit(val_date)
        # Cushion so quantized LTV stays strictly inside the cap in force on val_date.
        assessed = money(prin / limit * Decimal("1.06"))
        gold.append({
            "pledge_no": f"PLG-BG-{i:06d}",
            "loan_no": lid,
            "gross_g": "36.00",
            "net_g": "34.40",
            "purity": "22K",
            "assessed_inr": assessed,
        })
        gold_ops.append({
            "packet_id": f"PKT-BG-{i:06d}",
            "pledge_no": f"PLG-BG-{i:06d}",
            "loan_no": lid,
            "kind": "VALUATION",
            "valuation_date": val_date,
            "gross_g": "36.00",
            "net_g": "34.40",
            "purity": "22K",
            "assessed_inr": assessed,
            "custody_state": "VAULT",
            "principal": prin,
        })
    if code in {"TW", "UV"}:
        dlr = dealers()[i % len(dealers())]
        vin = f"MBJ{code}{i:010d}"[:17]
        veh.append({"loan_no": lid, "vin": vin, "dealer_code": dlr["dealer_code"]})
        comm = money(prin * Decimal("0.018" if code == "TW" else "0.015"))
        s6.append({
            "commission_id": f"COM-BG-{i:06d}",
            "loan_no": lid,
            "dealer_code": dlr["dealer_code"],
            "vin": vin,
            "invoice_no": f"INV-BG-{i:06d}",
            "amount": comm,
            "paid_date": origin + timedelta(days=2),
            "disb_no": f"{lid}-DISB",
        })
        ins.append({
            "ins_id": f"INS-BG-{i:06d}",
            "loan_no": lid,
            "product": "CREDIT_LIFE",
            "premium": money(1200),
            "sold_on": origin,
        })
    s4 = []
    if i < 10:
        s4.append({
            "event_id": f"COL-BG-PTP-{i:06d}",
            "loan_ref": lid,
            "agent_code": "A-SOUTH-03",
            "kind": "PTP_MADE",
            "event_date": date(2026, 7, 4),
            "amount": e,
        })
        s4.append({
            "event_id": f"COL-BG-KEPT-{i:06d}",
            "loan_ref": lid,
            "agent_code": "A-SOUTH-03",
            "kind": "PTP_KEPT",
            "event_date": date(2026, 7, 8),
            "amount": e,
        })
    elif i < 15:
        s4.append({
            "event_id": f"COL-BG-PTP-{i:06d}",
            "loan_ref": lid,
            "agent_code": "A-NORTH-02",
            "kind": "PTP_MADE",
            "event_date": date(2026, 7, 6),
            "amount": e,
        })
    if dpd >= 90:
        s4.append({
            "event_id": f"COL-BG-CALL-{i:06d}",
            "loan_ref": lid,
            "agent_code": "A-EAST-04",
            "kind": "CALL",
            "event_date": date(2026, 8, 20),
            "amount": money(0),
        })
    return {
        "loans": [loan],
        "disbursements": [{
            "disb_no": f"{lid}-DISB",
            "loan_no": lid,
            "amount": prin,
            "disb_date": origin,
            "seq": 1,
            "is_topup": False,
        }],
        "schedules": [{
            "schedule_id": f"{lid}-SCH",
            "loan_no": lid,
            "version": 1,
            "effective_from": origin,
            "emi_amount": e,
            "tenor_m": tenor,
        }],
        "instalments": insts,
        "payments_applied": pays,
        "allocations": allocs,
        "s2": s2,
        "s8": gl,
        "gold_pledge": gold,
        "s5": gold_ops,
        "vehicle": veh,
        "s6": s6,
        "insurance": ins,
        "s4": s4,
    }


def build_estate(scale: str, seed: int) -> Estate:
    cfg = SCALES[scale]
    e = Estate(scale=scale, seed=seed)
    e.rule_set = list(RULES)
    e.masters = _masters()
    e.identity_override = [
        {
            "pan": t.pan,
            "digital_cif": t.digital_cif,
            "gold_cif": t.gold_cif,
            "name_lms": t.name_lms,
            "name_gold": t.name_gold,
            "name_bureau": t.name_bureau,
        }
        for t in TWINS
    ]
    named = seed_incidents()
    _extend(e, named)

    seen_cif = {c["cif"] for c in e.customers}
    for c in e.customers:
        e.kyc.append(_kyc_for(c, "2024-09-15"))
        if not any(r.get("AccountNumber") and r.get("cif_hint") == c["cif"] for r in e.s7):
            e.s7.append({
                "AccountNumber": f"CRM-{c['cif'][-4:]}",
                "Name": c["legal_name"],
                "cif_hint": c["cif"],
                "consent": True,
            })

    for app in e.applications:
        dec = next((d for d in e.decisions if d["appl_no"] == app["appl_no"]), None)
        if dec:
            e.bureau_pull.append({
                "enquiry_ref": f"ENQ-{app['appl_no']}",
                "appl_no": app["appl_no"],
                "cif": app["cif"],
                "score": dec.get("score_used"),
                "pulled_on": app["applied_on"],
            })

    n_cust = int(cfg["customers"])
    n_loans = int(cfg["bg_loans"])
    pay_depth = int(cfg.get("pay_depth", 8))
    bg_customers = []
    for i in range(n_cust):
        c = _bg_customer(i)
        if c["cif"] in seen_cif:
            continue
        bg_customers.append(c)
        e.customers.append(c)
        e.kyc.append(_kyc_for(c))

    for i in range(n_loans):
        cust = bg_customers[i % len(bg_customers)]
        _extend(e, _bg_loan(i, cust, pay_depth=pay_depth))

    # Light bureau history for a slice (named already have S3)
    have_pan = {r.get("pan") for r in e.s3}
    for i, c in enumerate(e.customers[: min(120, len(e.customers))]):
        if c["pan"] in have_pan:
            continue
        e.s3.append({
            "bureau_id": f"CRIF-BG-{i:04d}",
            "pan": c["pan"],
            "score": 700 + (i % 90),
            "reported_as_of": date(2026, 7, 31),
            "enquiry_ref": f"ENQ-BG-{i:04d}",
            "cif_hint": c["cif"],
            "active_tradelines": 2,
            "enquiries_90d": 1,
            "worst_dpd_24m": 0,
            "reported_outstanding": money(0),
        })

    return e
