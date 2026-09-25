"""Fifteen causal incidents and eight near-misses. Reserved keys. Deterministic."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from .constants import money
from .identity import TWINS
from .money import allocate, emi
from .rules import gold_ltv_limit, waterfall_order

IST = ZoneInfo("Asia/Kolkata")


def _dt(d: date, hh: int, mm: int = 0) -> str:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=IST).isoformat()


def seed_incidents() -> dict:
    """Return tables + ground_truth list."""
    t = TWINS[0]
    rows: dict[str, list] = {k: [] for k in (
        "customers", "applications", "decisions", "loans", "disbursements",
        "instalments", "charges", "payments_applied", "allocations",
        "moratoriums", "write_offs", "recoveries", "s2", "s3", "s4", "s5",
        "s6", "s7", "s8", "gold_pledge", "vehicle", "incentives", "campaigns",
        "ground_truth",
    )}

    def cust(cif, name, pan, mobile, branch="PNQ-KTH"):
        rows["customers"].append({
            "cif": cif, "legal_name": name, "pan": pan, "mobile": mobile,
            "branch_code": branch, "dob": "1988-03-12",
        })

    cust(t.digital_cif, t.name_lms, t.pan, t.mobile_digital)
    cust(t.gold_cif, t.name_gold, t.pan, t.mobile_gold, "PNQ-KTH")
    # extra named people
    named = [
        ("AF-00010010", "Kavita Deshmukh", "AHWPK2010K", "9822020101", "PL"),
        ("AF-00010011", "Rahul Menon", "AHWPK2011L", "9822020102", "EDU"),
        ("AF-00010012", "Farhan Shaikh", "AHWPK2012M", "9822020103", "PL"),
        ("AF-00010013", "Priya Nair", "AHWPK2013N", "9822020104", "TW"),
        ("AF-00010014", "Amit Joshi", "AHWPK2014P", "9822020105", "PL"),
        ("AF-00010015", "Sneha Kulkarni", "AHWPK2015Q", "9822020106", "GOLD"),
        ("AF-00010016", "Vikram Rao", "AHWPK2016R", "9822020107", "GOLD"),
        ("AF-00010017", "Neha Banerjee", "AHWPK2017S", "9822020108", "GOLD"),
        ("AF-00010018", "Imran Khan", "AHWPK2018T", "9822020109", "GOLD"),
        ("AF-00010019", "Deepa Iyer", "AHWPK2019U", "9822020110", "PL"),
        ("AF-00010020", "Sanjay Gupta", "AHWPK2020V", "9822020111", "PL"),
        ("AF-00010021", "Meera Das", "AHWPK2021W", "9822020112", "PL"),
        ("AF-00010022", "Arun Pillai", "AHWPK2022X", "9822020113", "PL"),
        ("AF-00010023", "Pooja Mehta", "AHWPK2023Y", "9822020114", "BNPL"),
        ("AF-00010024", "Rohan Kulkarni", "AHWPK2024Z", "9822020115", "PL"),
    ]
    for cif, name, pan, mob, _ in named:
        cust(cif, name, pan, mob)

    def loan(no, cif, product, branch, principal, rate, tenor, start, status, dpd, **kw):
        live = status not in {"CLOSED", "SETTLED", "WRITTEN_OFF"}
        rec = {
            "loan_no": no, "cif": cif, "product_code": product, "branch_code": branch,
            "principal": money(principal), "annual_rate": Decimal(rate), "tenor_m": tenor,
            "start_date": start, "status": status, "dpd": dpd,
            "npa_flag": bool(dpd >= 90),
            "outstanding_principal": money(principal) if live else money(0),
            "parent_loan_no": kw.get("parent"),
        }
        rec.update(kw)
        rows["loans"].append(rec)
        return rec

    def gt(**kw):
        rows["ground_truth"].append(kw)

    # ── I01 paid at bank, overdue at LMS ──
    loan("AF-LN-I01-PL", "AF-00010010", "PL", "PNQ-HIN", 120000, "0.1800", 24, date(2025, 6, 5), "ACTIVE", 18)
    rows["instalments"].append({
        "instalment_id": "INS-I01", "loan_no": "AF-LN-I01-PL",
        "due_date": date(2026, 8, 3), "amount": money(6052.14), "status": "OVERDUE",
        "principal_due": money(4200), "interest_due": money(1852.14), "charge_due": money(0),
    })
    rows["s2"].append({
        "txn_ref": "UPI-I01-8891", "utr": "RBIUPI00I01A", "channel": "UPI",
        "status": "SUCCESS", "amount": money(6052.14),
        "event_date": date(2026, 8, 3), "value_date": date(2026, 8, 3),
        "settlement_date": date(2026, 8, 4), "ingested_at": _dt(date(2026, 8, 3), 21, 12),
        "loan_hint": "AF-LN-I01-PL", "mandate_id": "MND-I01",
    })
    rows["s8"].append({
        "je_id": "JE-I01", "posted_date": date(2026, 8, 4), "account_code": "LOAN-CONTROL",
        "amount": money(6052.14), "loan_ref": "", "source": "CASH_BATCH",
    })
    gt(incident_id="I01", kind="valid", customer_cif="AF-00010010", loan_no="AF-LN-I01-PL",
       product_code="PL", branch_code="PNQ-HIN", owner_email="finance.controller@aarohan.example",
       severity="high", monitor_id="M1", expected_detection=True,
       causal_event="UPI success 2026-08-03 21:12 IST; LMS apply job skipped",
       expected_action="Apply receipt or unmatched-cash",
       source_records={"s2_txn_ref": "UPI-I01-8891", "instalment_id": "INS-I01"})

    # I01n near-miss: applied next morning
    loan("AF-LN-I01N-PL", "AF-00010010", "PL", "PNQ-HIN", 80000, "0.1800", 18, date(2025, 7, 1), "ACTIVE", 0)
    rows["instalments"].append({
        "instalment_id": "INS-I01N", "loan_no": "AF-LN-I01N-PL",
        "due_date": date(2026, 8, 5), "amount": money(5100), "status": "PAID",
        "principal_due": money(3600), "interest_due": money(1500), "charge_due": money(0),
    })
    rows["s2"].append({
        "txn_ref": "UPI-I01N-11", "utr": "RBIUPI00I01N", "channel": "UPI",
        "status": "SUCCESS", "amount": money(5100),
        "event_date": date(2026, 8, 5), "value_date": date(2026, 8, 5),
        "settlement_date": date(2026, 8, 6), "ingested_at": _dt(date(2026, 8, 5), 22, 40),
        "loan_hint": "AF-LN-I01N-PL", "mandate_id": "MND-I01N",
    })
    rows["payments_applied"].append({
        "lms_receipt_no": "RCPT-I01N", "loan_no": "AF-LN-I01N-PL",
        "amount": money(5100), "value_date": date(2026, 8, 5),
        "posted_at": _dt(date(2026, 8, 6), 6, 10), "ext_txn_ref": "RBIUPI00I01N",
    })
    gt(incident_id="I01n", kind="near_miss", customer_cif="AF-00010010", loan_no="AF-LN-I01N-PL",
       product_code="PL", branch_code="PNQ-HIN", owner_email="finance.controller@aarohan.example",
       severity="high", monitor_id="M1", expected_detection=False,
       causal_event="UPI late evening; LMS applied 06:10 IST next day",
       expected_action="none", source_records={"s2_txn_ref": "UPI-I01N-11"})

    # ── I02 wrong waterfall ──
    p = money(150000)
    e = emi(p, Decimal("0.1800"), 36)
    loan("AF-LN-I02-PL", "AF-00010012", "PL", "MUM-AND", 150000, "0.1800", 36, date(2024, 11, 10), "ACTIVE", 0)
    rows["instalments"].append({
        "instalment_id": "INS-I02", "loan_no": "AF-LN-I02-PL",
        "due_date": date(2025, 5, 10), "amount": e,
        "status": "PARTIAL", "principal_due": money(2800), "interest_due": money(2200),
        "charge_due": money(500),
    })
    rows["payments_applied"].append({
        "lms_receipt_no": "RCPT-I02", "loan_no": "AF-LN-I02-PL",
        "amount": money(4000), "value_date": date(2025, 5, 12),
        "posted_at": _dt(date(2025, 5, 12), 11), "ext_txn_ref": "NACH-I02",
    })
    rows["s2"].append({
        "txn_ref": "NACH-I02", "utr": "NACH-I02", "channel": "NACH",
        "status": "SUCCESS", "amount": money(4000),
        "event_date": date(2025, 5, 12), "value_date": date(2025, 5, 12),
        "settlement_date": date(2025, 5, 13), "ingested_at": _dt(date(2025, 5, 12), 11),
        "loan_hint": "AF-LN-I02-PL", "mandate_id": "MND-I02",
    })
    rows["s8"].append({
        "je_id": "JE-I02", "posted_date": date(2025, 5, 13), "account_code": "CASH_BATCH",
        "amount": money(4000), "loan_ref": "AF-LN-I02-PL", "source": "CASH_BATCH",
    })
    # wrongly used v1
    bad = allocate(money(4000), money(500), money(2200), money(2800), ("CHARGE", "INTEREST", "PRINCIPAL"))
    for i, comp in enumerate(("CHARGE", "INTEREST", "PRINCIPAL"), 1):
        rows["allocations"].append({
            "lms_receipt_no": "RCPT-I02", "seq": i, "component": comp, "amount": bad[comp],
        })
    gt(incident_id="I02", kind="valid", customer_cif="AF-00010012", loan_no="AF-LN-I02-PL",
       product_code="PL", branch_code="MUM-AND", owner_email="finance.controller@aarohan.example",
       severity="high", monitor_id="M3", expected_detection=True,
       causal_event="Partial ₹4000 on 2025-05-12 allocated charges-first after v2",
       expected_action="Reverse and re-allocate INTEREST→CHARGE→PRINCIPAL",
       source_records={"lms_receipt_no": "RCPT-I02"})

    # I02n v1 still valid
    loan("AF-LN-I02N-PL", "AF-00010012", "PL", "MUM-AND", 90000, "0.1800", 24, date(2024, 10, 1), "ACTIVE", 0)
    rows["instalments"].append({
        "instalment_id": "INS-I02N", "loan_no": "AF-LN-I02N-PL",
        "due_date": date(2025, 3, 15), "amount": money(4500), "status": "PARTIAL",
        "principal_due": money(2000), "interest_due": money(1800), "charge_due": money(400),
    })
    rows["payments_applied"].append({
        "lms_receipt_no": "RCPT-I02N", "loan_no": "AF-LN-I02N-PL",
        "amount": money(3000), "value_date": date(2025, 3, 20),
        "posted_at": _dt(date(2025, 3, 20), 10), "ext_txn_ref": "NACH-I02N",
    })
    rows["s2"].append({
        "txn_ref": "NACH-I02N", "utr": "NACH-I02N", "channel": "NACH",
        "status": "SUCCESS", "amount": money(3000),
        "event_date": date(2025, 3, 20), "value_date": date(2025, 3, 20),
        "settlement_date": date(2025, 3, 21), "ingested_at": _dt(date(2025, 3, 20), 10),
        "loan_hint": "AF-LN-I02N-PL", "mandate_id": "MND-I02N",
    })
    rows["s8"].append({
        "je_id": "JE-I02N", "posted_date": date(2025, 3, 21), "account_code": "CASH_BATCH",
        "amount": money(3000), "loan_ref": "AF-LN-I02N-PL", "source": "CASH_BATCH",
    })
    ok = allocate(money(3000), money(400), money(1800), money(2000), waterfall_order("PL", date(2025, 3, 20)))
    for i, comp in enumerate(("CHARGE", "INTEREST", "PRINCIPAL"), 1):
        rows["allocations"].append({
            "lms_receipt_no": "RCPT-I02N", "seq": i, "component": comp, "amount": ok[comp],
        })
    gt(incident_id="I02n", kind="near_miss", customer_cif="AF-00010012", loan_no="AF-LN-I02N-PL",
       product_code="PL", branch_code="MUM-AND", owner_email="finance.controller@aarohan.example",
       severity="high", monitor_id="M3", expected_detection=False,
       causal_event="CHARGE-first on 2025-03-20 is WATERFALL v1",
       expected_action="none", source_records={"lms_receipt_no": "RCPT-I02N"})

    # ── I03 late charge inside grace ──
    loan("AF-LN-I03-PL", "AF-00010014", "PL", "BLR-JPN", 200000, "0.1800", 36, date(2025, 1, 8), "ACTIVE", 0)
    rows["instalments"].append({
        "instalment_id": "INS-I03", "loan_no": "AF-LN-I03-PL",
        "due_date": date(2026, 7, 8), "amount": money(7200), "status": "PAID",
        "principal_due": money(5000), "interest_due": money(2200), "charge_due": money(0),
    })
    rows["payments_applied"].append({
        "lms_receipt_no": "RCPT-I03", "loan_no": "AF-LN-I03-PL",
        "amount": money(7200), "value_date": date(2026, 7, 10),
        "posted_at": _dt(date(2026, 7, 10), 9), "ext_txn_ref": "UPI-I03",
    })
    rows["s2"].append({
        "txn_ref": "UPI-I03", "utr": "UPI-I03", "channel": "UPI",
        "status": "SUCCESS", "amount": money(7200),
        "event_date": date(2026, 7, 10), "value_date": date(2026, 7, 10),
        "settlement_date": date(2026, 7, 10), "ingested_at": _dt(date(2026, 7, 10), 9),
        "loan_hint": "AF-LN-I03-PL", "mandate_id": "",
    })
    rows["s8"].append({
        "je_id": "JE-I03", "posted_date": date(2026, 7, 11), "account_code": "CASH_BATCH",
        "amount": money(7200), "loan_ref": "AF-LN-I03-PL", "source": "CASH_BATCH",
    })
    rows["charges"].append({
        "charge_no": "CHG-I03", "loan_no": "AF-LN-I03-PL", "reason": "LATE",
        "amount": money(500), "event_date": date(2026, 7, 10),
        "posted_at": _dt(date(2026, 7, 11), 8), "due_date": date(2026, 7, 8),
    })
    gt(incident_id="I03", kind="valid", customer_cif="AF-00010014", loan_no="AF-LN-I03-PL",
       product_code="PL", branch_code="BLR-JPN", owner_email="product.pl@aarohan.example",
       severity="medium", monitor_id="M2", expected_detection=True,
       causal_event="Payment value_date due+2; PL grace 3; late charge still posted",
       expected_action="Reverse CHG-I03", source_records={"charge_no": "CHG-I03"})

    loan("AF-LN-I03N-PL", "AF-00010014", "PL", "BLR-JPN", 100000, "0.1800", 24, date(2025, 2, 1), "ACTIVE", 0)
    rows["charges"].append({
        "charge_no": "CHG-I03N", "loan_no": "AF-LN-I03N-PL", "reason": "LATE",
        "amount": money(500), "event_date": date(2026, 6, 12),
        "posted_at": _dt(date(2026, 6, 12), 8), "due_date": date(2026, 6, 8),
    })
    rows["payments_applied"].append({
        "lms_receipt_no": "RCPT-I03N", "loan_no": "AF-LN-I03N-PL",
        "amount": money(4800), "value_date": date(2026, 6, 12),
        "posted_at": _dt(date(2026, 6, 12), 10), "ext_txn_ref": "UPI-I03N",
    })
    rows["s2"].append({
        "txn_ref": "UPI-I03N", "utr": "UPI-I03N", "channel": "UPI",
        "status": "SUCCESS", "amount": money(4800),
        "event_date": date(2026, 6, 12), "value_date": date(2026, 6, 12),
        "settlement_date": date(2026, 6, 12), "ingested_at": _dt(date(2026, 6, 12), 10),
        "loan_hint": "AF-LN-I03N-PL", "mandate_id": "",
    })
    rows["s8"].append({
        "je_id": "JE-I03N", "posted_date": date(2026, 6, 13), "account_code": "CASH_BATCH",
        "amount": money(4800), "loan_ref": "AF-LN-I03N-PL", "source": "CASH_BATCH",
    })
    gt(incident_id="I03n", kind="near_miss", customer_cif="AF-00010014", loan_no="AF-LN-I03N-PL",
       product_code="PL", branch_code="BLR-JPN", owner_email="product.pl@aarohan.example",
       severity="medium", monitor_id="M2", expected_detection=False,
       causal_event="Payment due+4, outside grace", expected_action="none",
       source_records={"charge_no": "CHG-I03N"})

    # ── I04 moratorium EMI early ──
    loan("AF-LN-I04-EDU", "AF-00010011", "EDU", "CHN-TNG", 800000, "0.1150", 84, date(2024, 9, 15), "ACTIVE", 0)
    rows["moratoriums"].append({
        "loan_no": "AF-LN-I04-EDU", "start_date": date(2024, 9, 15),
        "end_date": date(2026, 9, 15), "course_end": date(2026, 3, 15), "grace_months": 6,
    })
    rows["instalments"].append({
        "instalment_id": "INS-I04", "loan_no": "AF-LN-I04-EDU",
        "due_date": date(2026, 8, 15), "amount": money(14500), "status": "DUE",
        "principal_due": money(8000), "interest_due": money(6500), "charge_due": money(0),
    })
    gt(incident_id="I04", kind="valid", customer_cif="AF-00010011", loan_no="AF-LN-I04-EDU",
       product_code="EDU", branch_code="CHN-TNG", owner_email="product.edu@aarohan.example",
       severity="high", monitor_id="M2", expected_detection=True,
       causal_event="EMI due 2026-08-15; moratorium ends 2026-09-15",
       expected_action="Withdraw EMI; extend moratorium", source_records={"instalment_id": "INS-I04"})

    # ── I05 incentive + reversal inside 7d ──
    loan("AF-LN-I05-PL", "AF-00010019", "PL", "MUM-AND", 180000, "0.1800", 36, date(2025, 3, 1), "ACTIVE", 42)
    rows["s2"].append({
        "txn_ref": "UPI-I05", "utr": "RBIUPI00I05A", "channel": "UPI",
        "status": "SUCCESS", "amount": money(8000),
        "event_date": date(2026, 7, 20), "value_date": date(2026, 7, 20),
        "settlement_date": date(2026, 7, 21), "ingested_at": _dt(date(2026, 7, 20), 14),
        "loan_hint": "AF-LN-I05-PL", "mandate_id": "",
    })
    rows["s2"].append({
        "txn_ref": "UPI-I05-REV", "utr": "RBIUPI00I05A", "channel": "UPI",
        "status": "REVERSED", "amount": money(8000),
        "event_date": date(2026, 7, 23), "value_date": date(2026, 7, 23),
        "settlement_date": date(2026, 7, 23), "ingested_at": _dt(date(2026, 7, 23), 9),
        "loan_hint": "AF-LN-I05-PL", "mandate_id": "",
    })
    rows["s4"].append({
        "event_id": "COL-I05", "loan_ref": "AF-LN-I05-PL", "agent_code": "A-WEST-07",
        "kind": "RECOVERY", "event_date": date(2026, 7, 20), "amount": money(8000),
    })
    rows["incentives"].append({
        "incentive_id": "INC-I05", "agent_code": "A-WEST-07", "loan_no": "AF-LN-I05-PL",
        "amount": money(200), "paid_date": date(2026, 7, 21),
        "recovery_value_date": date(2026, 7, 20),
    })
    gt(incident_id="I05", kind="valid", customer_cif="AF-00010019", loan_no="AF-LN-I05-PL",
       product_code="PL", branch_code="MUM-AND",
       owner_email="collections.mgr.west@aarohan.example",
       severity="high", monitor_id="M5", expected_detection=True,
       causal_event="Incentive 21 Jul; UPI reversed 23 Jul (T+3)",
       expected_action="Clawback INC-I05", source_records={"incentive_id": "INC-I05"})

    loan("AF-LN-I05N-PL", "AF-00010019", "PL", "MUM-AND", 70000, "0.1800", 18, date(2025, 4, 1), "ACTIVE", 20)
    rows["s2"].append({
        "txn_ref": "UPI-I05N", "utr": "RBIUPI00I05N", "channel": "UPI",
        "status": "SUCCESS", "amount": money(3000),
        "event_date": date(2026, 6, 1), "value_date": date(2026, 6, 1),
        "settlement_date": date(2026, 6, 2), "ingested_at": _dt(date(2026, 6, 1), 12),
        "loan_hint": "AF-LN-I05N-PL", "mandate_id": "",
    })
    rows["s2"].append({
        "txn_ref": "UPI-I05N-REV", "utr": "RBIUPI00I05N", "channel": "UPI",
        "status": "REVERSED", "amount": money(3000),
        "event_date": date(2026, 6, 12), "value_date": date(2026, 6, 12),
        "settlement_date": date(2026, 6, 12), "ingested_at": _dt(date(2026, 6, 12), 9),
        "loan_hint": "AF-LN-I05N-PL", "mandate_id": "",
    })
    rows["incentives"].append({
        "incentive_id": "INC-I05N", "agent_code": "A-WEST-07", "loan_no": "AF-LN-I05N-PL",
        "amount": money(75), "paid_date": date(2026, 6, 2),
        "recovery_value_date": date(2026, 6, 1),
    })
    gt(incident_id="I05n", kind="near_miss", customer_cif="AF-00010019", loan_no="AF-LN-I05N-PL",
       product_code="PL", branch_code="MUM-AND",
       owner_email="collections.mgr.west@aarohan.example",
       severity="high", monitor_id="M5", expected_detection=False,
       causal_event="Reversal T+11, outside 7-day clawback", expected_action="none",
       source_records={"incentive_id": "INC-I05N"})

    # ── I06 wrong agent ──
    loan("AF-LN-I06-PL", "AF-00010020", "PL", "AHM-SG", 110000, "0.1800", 24, date(2025, 5, 1), "ACTIVE", 55)
    rows["s4"].append({
        "event_id": "COL-I06", "loan_ref": "AF-LN-I06-PL", "agent_code": "A-WEST-07",
        "kind": "RECOVERY", "event_date": date(2026, 8, 10), "amount": money(5000),
    })
    rows["incentives"].append({
        "incentive_id": "INC-I06", "agent_code": "A-WEST-12", "loan_no": "AF-LN-I06-PL",
        "amount": money(125), "paid_date": date(2026, 8, 11),
        "recovery_value_date": date(2026, 8, 10),
    })
    rows["s2"].append({
        "txn_ref": "CASH-I06", "utr": "", "channel": "CASH",
        "status": "SUCCESS", "amount": money(5000),
        "event_date": date(2026, 8, 10), "value_date": date(2026, 8, 10),
        "settlement_date": date(2026, 8, 10), "ingested_at": _dt(date(2026, 8, 10), 17),
        "loan_hint": "AF-LN-I06-PL", "mandate_id": "",
    })
    rows["payments_applied"].append({
        "lms_receipt_no": "RCPT-I06", "loan_no": "AF-LN-I06-PL",
        "amount": money(5000), "value_date": date(2026, 8, 10),
        "posted_at": _dt(date(2026, 8, 10), 17), "ext_txn_ref": "CASH-I06",
    })
    rows["s8"].append({
        "je_id": "JE-I06", "posted_date": date(2026, 8, 11), "account_code": "CASH_BATCH",
        "amount": money(5000), "loan_ref": "AF-LN-I06-PL", "source": "CASH_BATCH",
    })
    gt(incident_id="I06", kind="valid", customer_cif="AF-00010020", loan_no="AF-LN-I06-PL",
       product_code="PL", branch_code="AHM-SG",
       owner_email="collections.mgr.west@aarohan.example",
       severity="medium", monitor_id="M5", expected_detection=True,
       causal_event="Collected by A-WEST-07; paid A-WEST-12",
       expected_action="Clawback and pay collecting agent",
       source_records={"incentive_id": "INC-I06"})

    # ── I07 dealer dup disb ──
    loan("AF-LN-I07-TW", "AF-00010013", "TW", "HYD-BAN", 95000, "0.1550", 24, date(2026, 2, 2), "ACTIVE", 0)
    rows["disbursements"].append({
        "disb_no": "AF-DSB-I07-1", "loan_no": "AF-LN-I07-TW", "amount": money(95000),
        "disb_date": date(2026, 2, 2), "seq": 1, "is_topup": False,
    })
    rows["disbursements"].append({
        "disb_no": "AF-DSB-I07-2", "loan_no": "AF-LN-I07-TW", "amount": money(95000),
        "disb_date": date(2026, 2, 2), "seq": 2, "is_topup": False,
    })
    rows["s6"].append({
        "commission_id": "COM-I07", "loan_no": "AF-LN-I07-TW", "dealer_code": "DL-HYD-01",
        "vin": "MBJTW07I07XXXX", "invoice_no": "DI-I07",
        "amount": money(1900), "paid_date": date(2026, 2, 4), "disb_no": "AF-DSB-I07-2",
    })
    rows["vehicle"].append({
        "loan_no": "AF-LN-I07-TW", "vin": "MBJTW07I07XXXX", "dealer_code": "DL-HYD-01",
    })
    rows["s8"].append({
        "je_id": "JE-I07", "posted_date": date(2026, 2, 4), "account_code": "DEALER-COMM",
        "amount": money(1900), "loan_ref": "AF-LN-I07-TW", "source": "MANUAL",
    })
    gt(incident_id="I07", kind="valid", customer_cif="AF-00010013", loan_no="AF-LN-I07-TW",
       product_code="TW", branch_code="HYD-BAN", owner_email="dealer.mgr@aarohan.example",
       severity="high", monitor_id="M10", expected_detection=True,
       causal_event="Commission on duplicate first disbursement AF-DSB-I07-2",
       expected_action="Recover commission; reverse duplicate disb",
       source_records={"commission_id": "COM-I07"})

    loan("AF-LN-I07N-TW", "AF-00010013", "TW", "HYD-BAN", 60000, "0.1550", 18, date(2025, 8, 1), "ACTIVE", 0)
    rows["disbursements"].append({
        "disb_no": "AF-DSB-I07N-1", "loan_no": "AF-LN-I07N-TW", "amount": money(60000),
        "disb_date": date(2025, 8, 1), "seq": 1, "is_topup": False,
    })
    rows["disbursements"].append({
        "disb_no": "AF-DSB-I07N-2", "loan_no": "AF-LN-I07N-TW", "amount": money(20000),
        "disb_date": date(2026, 1, 10), "seq": 2, "is_topup": True,
    })
    gt(incident_id="I07n", kind="near_miss", customer_cif="AF-00010013", loan_no="AF-LN-I07N-TW",
       product_code="TW", branch_code="HYD-BAN", owner_email="dealer.mgr@aarohan.example",
       severity="high", monitor_id="M10", expected_detection=False,
       causal_event="Second disb is a top-up; no commission paid",
       expected_action="none", source_records={"disb_no": "AF-DSB-I07N-2"})

    # ── I08 / I08n credit ──
    rows["applications"].append({
        "appl_no": "AF-AP-I08", "cif": "AF-00010021", "product_code": "PL",
        "applied_on": date(2026, 3, 1), "amount": money(250000),
    })
    rows["s3"].append({
        "bureau_id": "CRIF-I08", "pan": "AHWPK2021W", "score": 671,
        "reported_as_of": date(2026, 2, 28), "enquiry_ref": "ENQ-I08",
        "cif_hint": "AF-00010021",
    })
    rows["decisions"].append({
        "appl_no": "AF-AP-I08", "decided_on": date(2026, 3, 4), "outcome": "APPROVED",
        "score_used": 671, "override_flag": False, "loan_no": "AF-LN-I08-PL",
    })
    loan("AF-LN-I08-PL", "AF-00010021", "PL", "DEL-SKT", 250000, "0.1800", 36, date(2026, 3, 6), "ACTIVE", 0)
    gt(incident_id="I08", kind="valid", customer_cif="AF-00010021", loan_no="AF-LN-I08-PL",
       product_code="PL", branch_code="DEL-SKT", owner_email="credit.mgr@aarohan.example",
       severity="high", monitor_id="M6", expected_detection=True,
       causal_event="Sanction at 671 vs cutoff 680, no override",
       expected_action="Exception file or cancel path", source_records={"appl_no": "AF-AP-I08"})

    rows["applications"].append({
        "appl_no": "AF-AP-I08N", "cif": "AF-00010022", "product_code": "PL",
        "applied_on": date(2026, 3, 2), "amount": money(180000),
    })
    rows["s3"].append({
        "bureau_id": "CRIF-I08N", "pan": "AHWPK2022X", "score": 671,
        "reported_as_of": date(2026, 2, 28), "enquiry_ref": "ENQ-I08N",
        "cif_hint": "AF-00010022",
    })
    rows["decisions"].append({
        "appl_no": "AF-AP-I08N", "decided_on": date(2026, 3, 5), "outcome": "APPROVED",
        "score_used": 671, "override_flag": True, "loan_no": "AF-LN-I08N-PL",
        "override_by": "credit.mgr@aarohan.example",
    })
    loan("AF-LN-I08N-PL", "AF-00010022", "PL", "DEL-SKT", 180000, "0.1800", 24, date(2026, 3, 7), "ACTIVE", 0)
    gt(incident_id="I08n", kind="near_miss", customer_cif="AF-00010022", loan_no="AF-LN-I08N-PL",
       product_code="PL", branch_code="DEL-SKT", owner_email="credit.mgr@aarohan.example",
       severity="high", monitor_id="M6", expected_detection=False,
       causal_event="Same score with documented override", expected_action="none",
       source_records={"appl_no": "AF-AP-I08N"})

    # ── I09 repeat while TW is 120 DPD + campaign ──
    loan("AF-LN-I09-TW", "AF-00010013", "TW", "HYD-BAN", 80000, "0.1550", 24, date(2024, 10, 1), "ACTIVE", 120)
    rows["applications"].append({
        "appl_no": "AF-AP-I09", "cif": "AF-00010013", "product_code": "PL",
        "applied_on": date(2026, 7, 1), "amount": money(100000),
    })
    rows["decisions"].append({
        "appl_no": "AF-AP-I09", "decided_on": date(2026, 7, 3), "outcome": "APPROVED",
        "score_used": 710, "override_flag": False, "loan_no": "AF-LN-I09-PL",
    })
    loan("AF-LN-I09-PL", "AF-00010013", "PL", "HYD-BAN", 100000, "0.1800", 24, date(2026, 7, 4), "ACTIVE", 12)
    rows["campaigns"].append({
        "offer_id": "CMP-I09", "cif": "AF-00010013", "product_code": "PL",
        "offered_on": date(2026, 6, 28), "account_number": "CRM-0013",
    })
    rows["s7"].append({
        "AccountNumber": "CRM-0013", "Name": "Priya Nair", "cif_hint": "AF-00010013",
        "consent": True,
    })
    gt(incident_id="I09", kind="valid", customer_cif="AF-00010013", loan_no="AF-LN-I09-PL",
       product_code="PL", branch_code="HYD-BAN", owner_email="risk.mgr@aarohan.example",
       severity="critical", monitor_id="M6", expected_detection=True,
       causal_event="New PL while TW at 120 DPD; also offered CMP-I09",
       expected_action="Risk review; suppress campaign",
       source_records={"appl_no": "AF-AP-I09", "sibling": "AF-LN-I09-TW", "offer_id": "CMP-I09"})

    # ── I10 / I10n gold LTV ──
    loan("AF-LN-I10-GL", "AF-00010015", "GOLD", "PNQ-KTH", 164000, "0.1200", 6, date(2025, 8, 1), "ACTIVE", 10)
    rows["gold_pledge"].append({
        "pledge_no": "PLG-I10", "loan_no": "AF-LN-I10-GL", "gross_g": "42.00", "net_g": "40.00",
        "purity": "22K", "assessed_inr": money(200000),
    })
    rows["s5"].append({
        "packet_id": "PKT-I10", "pledge_no": "PLG-I10", "loan_no": "AF-LN-I10-GL",
        "kind": "VALUATION", "valuation_date": date(2025, 8, 12),
        "gross_g": "40.10", "net_g": "38.00", "purity": "22K",
        "assessed_inr": money(200000), "custody_state": "VAULT",
        "principal": money(164000),
    })
    # LTV 164000/200000 = 0.82 > 0.75
    assert gold_ltv_limit(date(2025, 8, 12)) == Decimal("0.75")
    gt(incident_id="I10", kind="valid", customer_cif="AF-00010015", loan_no="AF-LN-I10-GL",
       product_code="GOLD", branch_code="PNQ-KTH",
       owner_email="gold.ops.pnq-kth@aarohan.example",
       severity="high", monitor_id="M7", expected_detection=True,
       causal_event="LTV 82% on 2025-08-12 vs 75% cap",
       expected_action="Margin call / reval", source_records={"packet_id": "PKT-I10"})

    loan("AF-LN-I10N-GL", "AF-00010016", "GOLD", "PNQ-KTH", 164000, "0.1200", 6, date(2025, 6, 1), "CLOSED", 0)
    rows["s5"].append({
        "packet_id": "PKT-I10N", "pledge_no": "PLG-I10N", "loan_no": "AF-LN-I10N-GL",
        "kind": "VALUATION", "valuation_date": date(2025, 6, 15),
        "gross_g": "40.10", "net_g": "38.00", "purity": "22K",
        "assessed_inr": money(200000), "custody_state": "RELEASED",
        "principal": money(164000),
    })
    gt(incident_id="I10n", kind="near_miss", customer_cif="AF-00010016", loan_no="AF-LN-I10N-GL",
       product_code="GOLD", branch_code="PNQ-KTH",
       owner_email="gold.ops.pnq-kth@aarohan.example",
       severity="high", monitor_id="M7", expected_detection=False,
       causal_event="LTV 82% on 2025-06-15 when cap was 85%", expected_action="none",
       source_records={"packet_id": "PKT-I10N"})

    # ── I11 released while open ──
    loan("AF-LN-I11-GL", "AF-00010017", "GOLD", "MUM-AND", 90000, "0.1200", 6, date(2026, 1, 10), "ACTIVE", 5)
    rows["s5"].append({
        "packet_id": "PKT-I11", "pledge_no": "PLG-I11", "loan_no": "AF-LN-I11-GL",
        "kind": "RELEASE", "valuation_date": date(2026, 1, 10),
        "gross_g": "22.00", "net_g": "21.00", "purity": "22K",
        "assessed_inr": money(120000), "custody_state": "RELEASED",
        "principal": money(90000), "event_date": date(2026, 6, 2),
    })
    rows["gold_pledge"].append({
        "pledge_no": "PLG-I11", "loan_no": "AF-LN-I11-GL", "gross_g": "22.00", "net_g": "21.00",
        "purity": "22K", "assessed_inr": money(120000),
    })
    gt(incident_id="I11", kind="valid", customer_cif="AF-00010017", loan_no="AF-LN-I11-GL",
       product_code="GOLD", branch_code="MUM-AND",
       owner_email="gold.ops.mum-and@aarohan.example",
       severity="critical", monitor_id="M7", expected_detection=True,
       causal_event="Packet released 2026-06-02; loan still ACTIVE",
       expected_action="Recall packet or force-close loan",
       source_records={"packet_id": "PKT-I11"})

    # ── I12 stale valuation ──
    loan("AF-LN-I12-GL", "AF-00010018", "GOLD", "BLR-JPN", 70000, "0.1200", 12, date(2025, 11, 1), "ACTIVE", 0)
    rows["s5"].append({
        "packet_id": "PKT-I12", "pledge_no": "PLG-I12", "loan_no": "AF-LN-I12-GL",
        "kind": "VALUATION", "valuation_date": date(2025, 11, 1),
        "gross_g": "18.00", "net_g": "17.20", "purity": "22K",
        "assessed_inr": money(95000), "custody_state": "VAULT",
        "principal": money(70000),
    })
    gt(incident_id="I12", kind="valid", customer_cif="AF-00010018", loan_no="AF-LN-I12-GL",
       product_code="GOLD", branch_code="BLR-JPN",
       owner_email="gold.ops.blr-jpn@aarohan.example",
       severity="medium", monitor_id="M7", expected_detection=True,
       causal_event="Valuation 2025-11-01; 273 days at close vs 180 policy",
       expected_action="Revalue", source_records={"packet_id": "PKT-I12"})

    # ── I13 auction proceeds break ──
    loan("AF-LN-I13-GL", "AF-00010016", "GOLD", "PNQ-KTH", 110000, "0.1200", 6, date(2025, 9, 1), "SETTLED", 0)
    rows["s5"].append({
        "packet_id": "PKT-I13", "pledge_no": "PLG-I13", "loan_no": "AF-LN-I13-GL",
        "kind": "AUCTION", "valuation_date": date(2026, 5, 1),
        "gross_g": "28.00", "net_g": "26.50", "purity": "22K",
        "assessed_inr": money(140000), "custody_state": "AUCTIONED",
        "principal": money(110000), "proceeds_inr": money(120000),
        "event_date": date(2026, 6, 20),
    })
    rows["recoveries"].append({
        "rec_no": "REC-I13", "loan_no": "AF-LN-I13-GL", "amount": money(95000),
        "value_date": date(2026, 6, 20), "reason": "AUCTION",
    })
    rows["s8"].append({
        "je_id": "JE-I13", "posted_date": date(2026, 6, 21), "account_code": "AUCTION-SUSPENSE",
        "amount": money(120000), "loan_ref": "AF-LN-I13-GL", "source": "MANUAL",
    })
    gt(incident_id="I13", kind="valid", customer_cif="AF-00010016", loan_no="AF-LN-I13-GL",
       product_code="GOLD", branch_code="PNQ-KTH",
       owner_email="finance.controller@aarohan.example",
       severity="high", monitor_id="M8", expected_detection=True,
       causal_event="Proceeds 120000; settlement 95000; surplus missing",
       expected_action="Refund surplus / reclass suspense",
       source_records={"auction_id": "PKT-I13", "rec_no": "REC-I13"})

    # ── I14 / I14n write-off ──
    loan("AF-LN-I14-PL", "AF-00010020", "PL", "AHM-SG", 160000, "0.1800", 36, date(2025, 1, 1), "WRITTEN_OFF", 45)
    rows["write_offs"].append({
        "wo_no": "WO-I14", "loan_no": "AF-LN-I14-PL", "amount": money(18400),
        "posted_date": date(2026, 8, 1), "dpd_at": 45, "approval_ref": "",
    })
    rows["s8"].append({
        "je_id": "JE-I14", "posted_date": date(2026, 8, 1), "account_code": "WRITEOFF",
        "amount": money(18400), "loan_ref": "AF-LN-I14-PL", "source": "MANUAL",
    })
    gt(incident_id="I14", kind="valid", customer_cif="AF-00010020", loan_no="AF-LN-I14-PL",
       product_code="PL", branch_code="AHM-SG",
       owner_email="finance.controller@aarohan.example",
       severity="critical", monitor_id="M8", expected_detection=True,
       causal_event="WO 18400 at DPD 45, no approval",
       expected_action="Reverse or file approval", source_records={"wo_no": "WO-I14"})

    loan("AF-LN-I14N-PL", "AF-00010022", "PL", "DEL-SKT", 50000, "0.1800", 12, date(2025, 6, 1), "SETTLED", 40)
    rows["write_offs"].append({
        "wo_no": "WO-I14N", "loan_no": "AF-LN-I14N-PL", "amount": money(400),
        "posted_date": date(2026, 7, 15), "dpd_at": 40, "approval_ref": "",
    })
    gt(incident_id="I14n", kind="near_miss", customer_cif="AF-00010022", loan_no="AF-LN-I14N-PL",
       product_code="PL", branch_code="DEL-SKT",
       owner_email="finance.controller@aarohan.example",
       severity="critical", monitor_id="M8", expected_detection=False,
       causal_event="Residual 400 after settlement; below 500 materiality",
       expected_action="none", source_records={"wo_no": "WO-I14N"})

    # ── I15 recovery on sibling ──
    loan("AF-LN-I15-PL-A", "AF-00010021", "PL", "DEL-SKT", 140000, "0.1800", 36, date(2024, 12, 1), "WRITTEN_OFF", 200)
    loan("AF-LN-I15-PL-B", "AF-00010021", "PL", "DEL-SKT", 60000, "0.1800", 18, date(2025, 8, 1), "ACTIVE", 0)
    rows["write_offs"].append({
        "wo_no": "WO-I15", "loan_no": "AF-LN-I15-PL-A", "amount": money(22000),
        "posted_date": date(2026, 4, 1), "dpd_at": 200, "approval_ref": "CR-OK-15",
    })
    rows["recoveries"].append({
        "rec_no": "REC-I15", "loan_no": "AF-LN-I15-PL-B", "amount": money(6200),
        "value_date": date(2026, 8, 18), "reason": "POST_WO",
    })
    rows["s2"].append({
        "txn_ref": "NEFT-I15", "utr": "NEFT00I15AA", "channel": "NEFT",
        "status": "SUCCESS", "amount": money(6200),
        "event_date": date(2026, 8, 18), "value_date": date(2026, 8, 18),
        "settlement_date": date(2026, 8, 18), "ingested_at": _dt(date(2026, 8, 18), 13),
        "loan_hint": "AF-LN-I15-PL-A", "mandate_id": "",
    })
    gt(incident_id="I15", kind="valid", customer_cif="AF-00010021", loan_no="AF-LN-I15-PL-B",
       product_code="PL", branch_code="DEL-SKT",
       owner_email="finance.controller@aarohan.example",
       severity="high", monitor_id="M8", expected_detection=True,
       causal_event="Post-WO recovery posted to sibling PL-B; UTR hints PL-A",
       expected_action="Repost REC-I15 to AF-LN-I15-PL-A",
       source_records={"rec_no": "REC-I15", "wo_no": "WO-I15"})

    # ── M4 empty collection ──
    loan("AF-LN-M4-EMPTY", "AF-00010023", "BNPL", "DIGITAL", 8000, "0.2400", 6, date(2026, 1, 5), "ACTIVE", 38)
    for i in range(4):
        rows["s4"].append({
            "event_id": f"COL-M4-{i}", "loan_ref": "AF-LN-M4-EMPTY",
            "agent_code": "A-DIG-01", "kind": "CALL",
            "event_date": date(2026, 8, 20) + timedelta(days=i * 2), "amount": money(0),
        })
    gt(incident_id="M4-EMPTY", kind="valid", customer_cif="AF-00010023", loan_no="AF-LN-M4-EMPTY",
       product_code="BNPL", branch_code="DIGITAL",
       owner_email="collections.mgr.digital@aarohan.example",
       severity="medium", monitor_id="M4", expected_detection=True,
       causal_event="4 calls, no PTP kept, no S2 money",
       expected_action="Re-assign or escalate", source_records={"loan_no": "AF-LN-M4-EMPTY"})

    loan("AF-LN-M4-ZERO", "AF-00010023", "BNPL", "DIGITAL", 4000, "0.2400", 3, date(2026, 4, 1), "ACTIVE", 10)
    gt(incident_id="M4-ZERO", kind="near_miss", customer_cif="AF-00010023", loan_no="AF-LN-M4-ZERO",
       product_code="BNPL", branch_code="DIGITAL",
       owner_email="collections.mgr.digital@aarohan.example",
       severity="medium", monitor_id="M4", expected_detection=False,
       causal_event="Must not manufacture a case", expected_action="none",
       source_records={"loan_no": "AF-LN-M4-ZERO"})

    # M9 near-miss: gold top-up offered while unsecured DPD is 20 (below 30)
    loan("AF-LN-M9-OK-PL", "AF-00010024", "PL", "PNQ-KTH", 90000, "0.1800", 24, date(2025, 9, 1), "ACTIVE", 20)
    rows["campaigns"].append({
        "offer_id": "CMP-GOLD-OK", "cif": "AF-00010024", "product_code": "GOLD",
        "offered_on": date(2026, 7, 10), "account_number": "CRM-0024",
    })
    rows["s7"].append({
        "AccountNumber": "CRM-0024", "Name": "Rohan Kulkarni", "cif_hint": "AF-00010024",
        "consent": True,
    })
    gt(incident_id="M9-GOLD-OK", kind="near_miss", customer_cif="AF-00010024",
       loan_no="AF-LN-M9-OK-PL", product_code="GOLD", branch_code="PNQ-KTH",
       owner_email="product.crm@aarohan.example",
       severity="medium", monitor_id="M9", expected_detection=False,
       causal_event="Gold top-up offer; live PL DPD 20 is below XSELL 30",
       expected_action="none", source_records={"offer_id": "CMP-GOLD-OK"})

    return rows
