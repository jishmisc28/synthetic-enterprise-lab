#!/usr/bin/env python3
"""Byte-compare estate verification.json to the tiny contract. Exit 1 on drift."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "aarohan" / "verification.json"
EXPECTED = ROOT / "domains" / "aarohan" / "expected" / "tiny" / "verification.json"


def main() -> int:
    if not OUTPUT.exists():
        print(f"MISSING {OUTPUT}")
        return 1
    if not EXPECTED.exists():
        print(f"MISSING {EXPECTED}")
        return 1
    out = OUTPUT.read_bytes()
    exp = EXPECTED.read_bytes()
    if out != exp:
        print("DIFF output/aarohan/verification.json  domains/aarohan/expected/tiny/verification.json")
        return 1
    print("IDENTICAL  output/aarohan/verification.json == domains/aarohan/expected/tiny/verification.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
