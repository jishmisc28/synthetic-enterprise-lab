# Topology

This is the running shape after `make up`. Container names are prefixed with `synthetic-enterprise-lab-` by Compose.

| Client source | Process | Port | What you open |
|---|---|---|---|
| S1 loan book | `postgres-lms` behind `pgproxy` | 55432 | database `aarohan_lms`, schema `lms`, user `lms_ro` |
| S4 collections | `postgres-coll` | 55433 | database `aarohan_coll`, schema `coll`, user `coll_ro` |
| S8 ledger | `postgres-gl` | 55434 | database `aarohan_gl`, schema `gl`, user `gl_ro` |
| S5 vault | `postgres-gold` | 55435 | database `aarohan_gold`, schema `gold`, user `gold_ro` |
| S8 and S7 over HTTP | `erp` | 18080 | `/gl/journals`, `/crm/accounts`, `/crm/campaigns`, `/masters/*` |
| S2 events | `events` | 18081 | `GET /payments`, `/collections`, `/clickstream`. Pull only. |
| Health | `verify` | 18082 | `/`, `/catalog`, `/healthz`, `/verify` |
| Inbound webhook | `webhook` | 18083 | `POST /slack`, `GET /inbox` |
| Mail | `mailpit` | 18025, UI 18084 | SMTP catcher |
| S2, S3, S6, S9 files | `minio` | 19000, console 19001 | bucket `aarohan-landing` |

`postgres-archive` on port 55436 holds internal copies of the file and HTTP feeds (`aarohan_pay`, `aarohan_bureau`, `aarohan_veh`, `aarohan_crm`, `aarohan_masters`). The verifier counts them. A client that connects there and treats the copy as the system of record has skipped the protocol the domain is trying to test.

`lms-slow` delays the loan-book proxy only. Stopping MinIO does not stop Postgres. `erp-500` does not stop the ledger database.

Nine database names exist. Four of them are the client Postgres path. The other five are archive.

Cross-database `SELECT` without the optional foreign-data wrapper fails. That is intentional. Listing database names is not the same as reading them.

## Named disagreement

Loan `AF-LN-I01-PL`:

- Payments: `txn_ref=UPI-I01-8891`, status success, amount `6052.1400`, date 2026-08-03.
- Loan book: no applied row for that reference.
- Ledger: journal `JE-I01`, same amount, posted 2026-08-04, loan reference empty.

A second disagreement is weight, not cash. Pledge `PLG-I10` is 40 grams on the loan book and 38 grams in the vault, and only the vault has custody state.

K14 on the truth sheet is `0.6667` (promises kept over promises made, collections only). Promises kept that also match payment-feed money inside the promise window are 0. Both figures are the exercise.

## Chaos

| Command | Effect |
|---|---|
| `make break lms-slow` | Loan-book port stalls |
| `make break s2-late` | Payment event feed hides the last two days |
| `make break minio-down` | Object store stops. Loan counts stay |
| `make break erp-500` | ERP HTTP returns 500. Ledger Postgres stays up |
| `make heal` | Clears those switches and starts MinIO |
| `make advance` | Moves the event clock one day (`DAYS=n` to skip) |

`make down` removes volumes. A Docker restart without `down -v` keeps them.
