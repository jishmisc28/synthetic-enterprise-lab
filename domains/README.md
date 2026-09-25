# Domains

A **domain** is one industry’s IT estate. Synthetic Enterprise Lab is the lab; the domain is the business.

```
domains/<name>/
  README.md           what this industry is
  run.py              generate(scale, seed, out) → MANIFEST
  sql/                typed schemas + load.sql (if Postgres)
  expected/<scale>/   verification.json, ground_truth.json, hashes
  tests/              invariants that do not need Docker
```

The first domain is [`aarohan/`](aarohan/) — fintech / Indian NBFC lending.

## What a domain must provide

1. A generator that is deterministic on `(scale, seed)`.
2. A `verification.json` the health API can repeat.
3. Source instances added to `runtime/catalog.py` (or a domain catalog the runtime loads).
4. Money as `numeric(19,4)` if the domain has money. Computed in code, never by an LLM.
5. At least one cross-source disagreement. A single consistent warehouse is a failed pack.

## What a domain must not do

- Import an application package (`lib` or `app`).
- Fork `runtime/` or add a second compose file.
- Load the movement feed into the system of record.
- Change named incident keys when scale changes.

## Adding the next domain

1. Copy the folder shape, not Aarohan’s tables.
2. Register sources on the health catalog.
3. Keep `make up` / `make down` / `make verify` as the only operator commands.
4. Leave Aarohan numbers in Aarohan.

A second domain is not in this repository. Add one only when it has its own generator, truth sheet, and at least one cross-source disagreement.
