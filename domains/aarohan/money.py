"""Deterministic INR arithmetic. numeric(19,4) via Decimal."""

from __future__ import annotations

from decimal import Decimal

from .constants import money


def monthly_rate(annual: Decimal) -> Decimal:
    return annual / Decimal("12")


def emi(principal: Decimal, annual_rate: Decimal, n: int) -> Decimal:
    if n <= 0:
        return money(0)
    r = monthly_rate(annual_rate)
    if r == 0:
        return money(principal / n)
    one = Decimal("1")
    factor = (one + r) ** n
    return money(principal * r * factor / (factor - one))


def daily_accrual(outstanding: Decimal, annual_rate: Decimal, day_count: str) -> Decimal:
    den = Decimal("365") if day_count == "ACT365" else Decimal("360")
    return money(outstanding * annual_rate / den)


def allocate(amount: Decimal, charge_due: Decimal, interest_due: Decimal, principal_due: Decimal, order: tuple[str, ...]):
    """Return dict of allocated amounts. Unapplied leftover is 'UNAPPLIED'."""
    buckets = {
        "CHARGE": charge_due,
        "INTEREST": interest_due,
        "PRINCIPAL": principal_due,
    }
    out = {k: money(0) for k in buckets}
    rest = amount
    for name in order:
        take = min(rest, buckets[name])
        out[name] = money(take)
        rest = money(rest - take)
        if rest <= 0:
            break
    out["UNAPPLIED"] = money(rest)
    return out


WATERFALL_V1 = ("CHARGE", "INTEREST", "PRINCIPAL")
WATERFALL_V2 = ("INTEREST", "CHARGE", "PRINCIPAL")
