# Aarohan — fintech domain

A mid-market Indian NBFC whose systems do not agree. This folder is the **generator and the model**. The running processes live in Synthetic Enterprise Lab’s outer layer (`make up` from the repo root).

Seed `20260907`. Close date 2026-08-31. Window 2024-09-01 → 2026-08-31.

Aarohan is the first domain packed into Synthetic Enterprise Lab. Do not reuse its loan numbers, incident keys, or KPI values for another industry.

## Subsystems (what the generator emits)

| Id | System | Where it runs after `make up` |
|---|---|---|
| S1 | LMS (loans, customers, charges, dated rules) | Postgres process `postgres-lms` `:55432` db `aarohan_lms` |
| S2 | Payments (gateway / till / NACH) | MinIO `payments/` + events pull `:18081` (PG archive internal) |
| S3 | Bureau as-of | MinIO `bureau/` (PG archive internal) |
| S4 | Collections / PTP | Postgres process `postgres-coll` `:55433` |
| S5 | Gold vault (packets, custody) | Postgres process `postgres-gold` `:55435` |
| S6 | Dealer / vehicle commission | MinIO `vehicle/` (PG archive internal) |
| S7 | CRM (accounts, campaigns) | HTTP `:18080/crm/*` (PG archive internal) |
| S8 | GL + ERP HTTP | Postgres process `postgres-gl` `:55434` + ERP `:18080` |
| S9 | Masters / identity override | MinIO `masters/` (PG archive internal) |

Reasoning (joins, KPIs, messiness): [`../../docs/DATA_AND_MESSINESS.md`](../../docs/DATA_AND_MESSINESS.md).
Connect a product: [`../../docs/CONNECT.md`](../../docs/CONNECT.md).

## Generate without Docker

```bash
cd synthetic-enterprise-lab
PYTHONPATH=domains python3 -c "from aarohan.run import generate; generate('tiny', 20260907, __import__('pathlib').Path('output/aarohan'))"
```

## Layout

```
aarohan/
  run.py                 entry: generate(scale, seed, out)
  estate.py              builds the in-memory book
  emit.py                writes CSVs / JSON
  evaluate.py            verification + ground truth
  incidents.py           I01–I15 + near-misses
  rules.py / rules/      dated waterfall, LTV, …
  sql/00_lms_schema.sql  typed LMS
  sql/load.sql           valid \copy, dimensions first
  sql/20_kpis.sql        management questions
  sql/30_monitors.sql    M1–M10
  expected/tiny/         CI hashes and verification sheet
  tests/                 invariants
```

## Tests

```bash
PYTHONPATH=domains python3 -m unittest discover -s domains/aarohan/tests -v
```

Named incident keys (`AF-LN-I01-PL`, `CHG-I03`, …) do not change with scale.

## What must stay apart

- S2 payments are not `lms.payment_applied`.
- S5 `custody_state` is not a column on `lms.gold_pledge`.
- GL `CASH_BATCH` is T+1. Same-day LMS vs GL is `timing_not_break`.
- CIF twins are two CIFs, one PAN — not a primary-key collision.
- Do not redesign I01–I15 to make a load easier.
