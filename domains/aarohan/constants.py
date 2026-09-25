from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN

SEED = 20260907
ESTATE_TODAY = date(2026, 9, 7)
CLOSE_DATE = date(2026, 8, 31)
WINDOW_START = date(2024, 9, 1)
MONEY_Q = Decimal("0.0001")
GST = Decimal("0.18")

WATERFALL_V2_FROM = date(2025, 4, 1)
GOLD_LTV_TIGHTEN = date(2025, 7, 1)
SCORE_TIGHTEN = date(2025, 1, 1)
CLAWBACK_DAYS = 7
GOLD_REVAL_DAYS = 180
WRITEOFF_DPD = 180
WRITEOFF_RESIDUAL = Decimal("500.0000")

SCALES = {
    "tiny": {
        "customers": 140,
        "bg_loans": 80,
        "branches": 32,
        "pay_depth": 8,
    },
    # demo == the running-stack default. Same named keys as tiny/full.
    "demo": {
        "customers": 40000,
        "bg_loans": 90000,
        "branches": 32,
        "pay_depth": 12,
    },
    "full": {
        "customers": 40000,
        "bg_loans": 90000,
        "branches": 32,
        "pay_depth": 8,
    },
    "stress": {
        "customers": 120000,
        "bg_loans": 280000,
        "branches": 32,
        "pay_depth": 8,
    },
}


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_Q, rounding=ROUND_HALF_EVEN)
