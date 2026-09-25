# Changelog

## 0.1.0

First public release of the lab.

- One compose stack: separate Postgres processes for the loan book, collections, vault, and ledger.
- File and HTTP feeds for payments, bureau, dealer files, CRM, and masters.
- Aarohan tiny domain, seed `20260907`, with a verification sheet and named disagreements.
- `make test` without Docker. `make up`, `make verify`, `make break`, and `make down` for the running estate.
