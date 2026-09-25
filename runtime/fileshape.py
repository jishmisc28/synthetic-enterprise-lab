"""Partner file shapes: xlsx (merged headers + total), jsonl, gzip csv, cp1252."""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

ESTATE = Path("/data/output/aarohan")
LANDING = Path("/data/landing")


def _read(rel: str) -> tuple[list[str], list[dict]]:
    path = ESTATE / rel
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys()) if rows else []
        return fields, rows


def drop_wave(wave: int) -> list[str]:
    """Drop one partner-shaped file. Waves are sequential, not all at once."""
    LANDING.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    if wave == 0:
        written.append(_gzip_payments())
    elif wave == 1:
        written.append(_xlsx_collections())
    elif wave == 2:
        written.append(_jsonl_bureau())
    elif wave == 3:
        written.append(_cp1252_commissions())
    elif wave == 4:
        written.append(_fixed_width_identity())
    return [p for p in written if p]


def _gzip_payments() -> str:
    dest = LANDING / "payments" / "upi_2026-08.csv.gz"
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = ESTATE / "files" / "payments" / "upi.csv"
    if not src.exists():
        return ""
    dest.write_bytes(gzip.compress(src.read_bytes()))
    return str(dest)


def _xlsx_collections() -> str:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    dest = LANDING / "collections" / "ptp_register.xlsx"
    dest.parent.mkdir(parents=True, exist_ok=True)
    _, rows = _read("files/collections/events.csv")
    wb = Workbook()
    ws = wb.active
    ws.title = "PTP"
    ws.merge_cells("A1:F1")
    ws["A1"] = "Aarohan Collections — promise-to-pay register (partner export)"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A2:F2")
    ws["A2"] = "Region West / South  |  partner export  |  do not parse row 1–2"
    ws["A2"].alignment = Alignment(horizontal="left")
    headers = ["event_id", "loan_ref", "agent_code", "kind", "event_date", "amount"]
    for col, h in enumerate(headers, start=1):
        ws.cell(3, col, h).font = Font(bold=True)
    total = 0.0
    for i, row in enumerate(rows, start=4):
        for col, h in enumerate(headers, start=1):
            ws.cell(i, col, row.get(h, ""))
        try:
            total += float(row.get("amount") or 0)
        except ValueError:
            pass
    end = 4 + len(rows)
    ws.cell(end, 1, "TOTAL")
    ws.cell(end, 6, f"{total:.4f}")
    ws.cell(end, 1).font = Font(bold=True)
    wb.save(dest)
    return str(dest)


def _jsonl_bureau() -> str:
    dest = LANDING / "bureau" / "bureau_2026-07.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    _, rows = _read("files/bureau/bureau_2026-07.csv")
    with dest.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(dest)


def _cp1252_commissions() -> str:
    dest = LANDING / "vehicle" / "commissions_partner.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    fields, rows = _read("files/vehicle/commissions.csv")
    # Partner file: Windows-1252 with a rupee-adjacent smart quote and an em-dash.
    with dest.open("w", encoding="cp1252", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(fields + ["notes"])
        for row in rows:
            note = "Dealer remit \x96 pending"  # en-dash in cp1252
            w.writerow([row.get(k, "") for k in fields] + [note])
    return str(dest)


def _fixed_width_identity() -> str:
    dest = LANDING / "masters" / "identity_override.fwf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    _, rows = _read("files/masters/identity_override.csv")
    spec = (("pan", 10), ("digital_cif", 12), ("gold_cif", 12), ("name_lms", 24))
    lines = ["".join(name.ljust(width) for name, width in spec)]
    for row in rows:
        lines.append("".join(str(row.get(name, ""))[:width].ljust(width) for name, width in spec))
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(dest)


def waves_present() -> list[str]:
    if not LANDING.exists():
        return []
    return sorted(str(p.relative_to(LANDING)) for p in LANDING.rglob("*") if p.is_file())
