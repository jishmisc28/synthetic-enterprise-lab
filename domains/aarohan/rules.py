"""Versioned rules. This module is the payload; JSON is a dump of RULES."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .constants import GOLD_LTV_TIGHTEN, SCORE_TIGHTEN, WATERFALL_V2_FROM
from .money import WATERFALL_V1, WATERFALL_V2

RULES: list[dict] = [
    {"rule_code": "WATERFALL", "product_code": "PL", "effective_from": "2024-09-01",
     "effective_to": "2025-03-31", "payload": {"order": list(WATERFALL_V1)}},
    {"rule_code": "WATERFALL", "product_code": "PL", "effective_from": "2025-04-01",
     "effective_to": None, "payload": {"order": list(WATERFALL_V2)}},
    {"rule_code": "WATERFALL", "product_code": "BNPL", "effective_from": "2024-09-01",
     "effective_to": "2025-03-31", "payload": {"order": list(WATERFALL_V1)}},
    {"rule_code": "WATERFALL", "product_code": "BNPL", "effective_from": "2025-04-01",
     "effective_to": None, "payload": {"order": list(WATERFALL_V2)}},
    {"rule_code": "WATERFALL", "product_code": "EDU", "effective_from": "2024-09-01",
     "effective_to": "2025-03-31", "payload": {"order": list(WATERFALL_V1)}},
    {"rule_code": "WATERFALL", "product_code": "EDU", "effective_from": "2025-04-01",
     "effective_to": None, "payload": {"order": list(WATERFALL_V2)}},
    {"rule_code": "WATERFALL", "product_code": "TW", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"order": list(WATERFALL_V1)}},
    {"rule_code": "WATERFALL", "product_code": "UV", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"order": list(WATERFALL_V1)}},
    {"rule_code": "WATERFALL", "product_code": "GOLD", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"order": list(WATERFALL_V1)}},
    {"rule_code": "GRACE_DAYS", "product_code": "PL", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"days": 3}},
    {"rule_code": "GRACE_DAYS", "product_code": "BNPL", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"days": 1}},
    {"rule_code": "GRACE_DAYS", "product_code": "TW", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"days": 5}},
    {"rule_code": "GRACE_DAYS", "product_code": "UV", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"days": 5}},
    {"rule_code": "GRACE_DAYS", "product_code": "EDU", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"days": 3}},
    {"rule_code": "GRACE_DAYS", "product_code": "GOLD", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"days": 0}},
    {"rule_code": "GOLD_LTV", "product_code": "GOLD", "effective_from": "2024-09-01",
     "effective_to": "2025-06-30", "payload": {"ltv": 0.85}},
    {"rule_code": "GOLD_LTV", "product_code": "GOLD", "effective_from": "2025-07-01",
     "effective_to": None, "payload": {"ltv": 0.75}},
    {"rule_code": "GOLD_REVAL_DAYS", "product_code": "GOLD", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"days": 180}},
    {"rule_code": "SCORE_CUTOFF", "product_code": "PL", "effective_from": "2024-09-01",
     "effective_to": "2024-12-31", "payload": {"min": 660}},
    {"rule_code": "SCORE_CUTOFF", "product_code": "PL", "effective_from": "2025-01-01",
     "effective_to": None, "payload": {"min": 680}},
    {"rule_code": "SCORE_CUTOFF", "product_code": "BNPL", "effective_from": "2025-01-01",
     "effective_to": None, "payload": {"min": 640}},
    {"rule_code": "SCORE_CUTOFF", "product_code": "TW", "effective_from": "2025-01-01",
     "effective_to": None, "payload": {"min": 660}},
    {"rule_code": "SCORE_CUTOFF", "product_code": "EDU", "effective_from": "2025-01-01",
     "effective_to": None, "payload": {"min": 700}},
    {"rule_code": "INCENTIVE", "product_code": "*", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"rate": 0.025, "clawback_days": 7}},
    {"rule_code": "DEALER_COMM", "product_code": "TW", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"rate": 0.02, "on_topup": False}},
    {"rule_code": "DEALER_COMM", "product_code": "UV", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"rate": 0.015, "on_topup": False}},
    {"rule_code": "REPEAT_BLOCK", "product_code": "*", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"max_sibling_dpd": 60}},
    {"rule_code": "XSELL_ELIG", "product_code": "*", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"max_dpd": 30}},
    {"rule_code": "WRITEOFF", "product_code": "*", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"min_dpd": 180, "residual_ok": 500.0}},
    {"rule_code": "DAY_COUNT", "product_code": "GOLD", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"method": "30360"}},
    {"rule_code": "DAY_COUNT", "product_code": "*", "effective_from": "2024-09-01",
     "effective_to": None, "payload": {"method": "ACT365"}},
]


def rule_as_of(rule_code: str, product: str, on: date) -> dict | None:
    iso = on.isoformat()
    hits = [
        r for r in RULES
        if r["rule_code"] == rule_code
        and r["product_code"] in (product, "*")
        and r["effective_from"] <= iso
        and (r["effective_to"] is None or r["effective_to"] >= iso)
    ]
    exact = [r for r in hits if r["product_code"] == product]
    return (exact or hits)[0] if (exact or hits) else None


def waterfall_order(product: str, value_date: date) -> tuple[str, ...]:
    row = rule_as_of("WATERFALL", product, value_date)
    if not row:
        return WATERFALL_V1
    return tuple(row["payload"]["order"])


def gold_ltv_limit(on: date) -> Decimal:
    row = rule_as_of("GOLD_LTV", "GOLD", on)
    return Decimal(str(row["payload"]["ltv"])) if row else Decimal("0.75")


def score_cutoff(product: str, on: date) -> int:
    row = rule_as_of("SCORE_CUTOFF", product, on)
    return int(row["payload"]["min"]) if row else 0


def grace_days(product: str, on: date) -> int:
    row = rule_as_of("GRACE_DAYS", product, on)
    return int(row["payload"]["days"]) if row else 0


# Silence unused imports used as documentation of the dated constants
_ = (WATERFALL_V2_FROM, GOLD_LTV_TIGHTEN, SCORE_TIGHTEN)
