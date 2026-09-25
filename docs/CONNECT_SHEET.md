# Aarohan connection sheet (current topology)

Hand this page to whoever connects a product. Dev credentials are lab fixtures, not secrets.

**Connect S1 LMS + S2 payments (MinIO or events pull) first.** That is I01: bank `UPI-I01-8891` SUCCESS `6052.1400` on 2026-08-03, LMS never applied it, GL `JE-I01` posted T+1 with an empty `loan_ref`.

S2 / S3 / S6 / S7 / S9 also have a Postgres archive on `:55436`. That archive is **internal**. Do not open it as the source. The client path is the transport in the table.

Host below is `127.0.0.1` on the Docker host, or the SSH jump host you tunnel to.

| Source | Client transport | Connection | Holds | Cadence | Intended failure |
|---|---|---|---|---|---|
| **S1 LMS** | Postgres | `127.0.0.1:55432` db `aarohan_lms` schema `lms` user `lms_ro` / `lms_ro_dev` | loans, customers, instalments, applied cash, dated `rule_set` | SoR, live | `lms-slow` (this port only). Process down ≠ GL down. |
| **S2 Payments** | MinIO files + events **pull** | S3 `http://127.0.0.1:19000` bucket `aarohan-landing` prefix `payments/` keys `aarohan` / `aarohan-minio-dev`. Events `http://127.0.0.1:18081/payments` `Authorization: Bearer aarohan-dev` | gateway / till / NACH / cash; three clocks | Dated objects; GET poll; `POST /advance` moves the clock | `minio-down` (feed down ≠ zero payments). `s2-late` withholds last 2 days on HTTP only. **No push** to a client URL. |
| **S3 Bureau** | MinIO files | same S3, prefix `bureau/` (`bureau/2026-07-31/bureau_2026-07.jsonl`) | PAN as-of pulls | Periodic file | `minio-down` |
| **S4 Collections** | Postgres | `127.0.0.1:55433` db `aarohan_coll` schema `coll` user `coll_ro` / `coll_ro_dev` | `coll.event`, `coll.incentive` (PTP kinds) | Ops system | Process independent of LMS. Partner xlsx is an overlay under `collections/`. |
| **S5 Gold vault** | Postgres | `127.0.0.1:55435` db `aarohan_gold` schema `gold` user `gold_ro` / `gold_ro_dev` | `gold.packet` including `custody_state` | SoR | Independent of LMS. Weights here disagree with `lms.gold_pledge`. |
| **S6 Dealer** | MinIO files | S3 prefix `vehicle/` (`vehicle/2026-08-31/commissions_partner.csv`, cp1252) | commissions | Partner drop | `minio-down` |
| **S7 CRM** | HTTP | `http://127.0.0.1:18080/crm/accounts` and `/crm/campaigns` `Authorization: Bearer aarohan-dev` cursor + `limit` | accounts, campaigns | SaaS poll | Missing bearer → **401**. `erp-500` → 500. |
| **S8 GL** | Postgres **and** ERP HTTP | PG `127.0.0.1:55434` db `aarohan_gl` schema `gl` user `gl_ro` / `gl_ro_dev`. HTTP `http://127.0.0.1:18080/gl/journals` same bearer, cursor (default 100, max 500, 199 rows) | journal lines | Nightly batch (T+1 cash) | `erp-500` kills HTTP only. PG stays up. |
| **S9 Masters** | MinIO files + ERP `/masters/*` | S3 prefix `masters/`. HTTP `/masters/{holidays,rates,…}` | identity override, human rule copy | Versioned files | Typed rules for metrics live on **S1** `lms.rule_set`. |

Events direction: **pull only**. `GET /payments?since=`. There is no Synthetic Enterprise Lab → client webhook. `:18083/slack` is the other way (product posts in).

K14 on the truth sheet is `0.6667` (10 `PTP_KEPT` / 15 `PTP_MADE` in S4). Kept-with-S2-money in the PTP window is `0`. Both numbers are the point. Do not “fix” them.

Ports and binds: [`PORTS.md`](PORTS.md). How to plug in: [`CONNECT.md`](CONNECT.md). Process map: [`TOPOLOGY.md`](TOPOLOGY.md).
