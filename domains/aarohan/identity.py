"""Imperfect identity. PAN is the steward key; CIF is not."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Twin:
    seq: int
    digital_cif: str
    gold_cif: str
    pan: str
    name_lms: str
    name_gold: str
    name_bureau: str
    mobile_digital: str
    mobile_gold: str


TWINS: list[Twin] = [
    Twin(1, "AF-00010001", "AF-00020001", "AHWPK1111A",
         "Ramesh Kumar", "RAMESH K", "RAMESH KUMAR", "9822011111", "9822099991"),
    Twin(2, "AF-00010002", "AF-00020002", "AHWPK1112B",
         "Sunita Patil", "SUNITA P", "SUNITA PATIL", "9822011112", "9822099992"),
    Twin(3, "AF-00010003", "AF-00020003", "AHWPK1113C",
         "Mohammed Irfan", "MD IRFAN", "MOHAMMED IRFAN", "9822011113", "9822099993"),
]


def norm_pan(p: str) -> str:
    return (p or "").strip().upper()


def norm_name(n: str) -> str:
    return " ".join((n or "").upper().replace(".", "").split())
