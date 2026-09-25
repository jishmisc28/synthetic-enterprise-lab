#!/usr/bin/env python3
"""Pretty-print GET /verify as a pass/fail table. Exit 1 on failure."""

from __future__ import annotations

import json
import sys
import urllib.request

URL = "http://127.0.0.1:18082/verify"


def main() -> int:
    try:
        with urllib.request.urlopen(URL, timeout=60) as resp:
            payload = json.loads(resp.read().decode())
            status = resp.status
    except Exception as exc:  # noqa: BLE001
        if hasattr(exc, "read"):
            raw = exc.read().decode(errors="replace")
            try:
                payload = json.loads(raw)
                status = getattr(exc, "code", 503)
            except Exception:
                print(f"VERIFY UNREACHABLE: {exc}")
                return 1
        else:
            print(f"VERIFY UNREACHABLE: {exc}")
            return 1

    print(f"scale={payload.get('scale')} seed={payload.get('seed')} today={payload.get('today')} chaos={payload.get('chaos')}")
    print("")
    print(f"{'CHECK':<28} {'OK':<6} DETAIL")
    print("-" * 100)
    for c in payload.get("checks", []):
        mark = "PASS" if c.get("ok") else "FAIL"
        if not c.get("required", True):
            mark = "SKIP" if c.get("ok") else "WARN"
        print(f"{c['check']:<28} {mark:<6} {c.get('detail', '')[:90]}")
    print("-" * 100)
    failed = payload.get("failed") or []
    if payload.get("ok") and status == 200:
        print("VERIFY PASS")
        return 0
    print("VERIFY FAIL")
    for f in failed:
        print(f"  - {f['check']}: {f['detail']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
