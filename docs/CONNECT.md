# Connect a product

Synthetic Enterprise Lab is already running the company’s systems. Your product is a client. Start the lab, then open one connection per source.

## 1. Start

```bash
make up
```

Open http://127.0.0.1:18082/ and wait until required sources are up.

On the machine that runs Docker, the host is `127.0.0.1`. If your product runs in another container, use `host.docker.internal` or the host gateway. Do not attach your product to this compose network.

## 2. One connection per source

S1, S4, S5, and S8 are separate Postgres processes. S2, S3, S6, and S9 are object-store prefixes. S7 is HTTP. The sheet is [CONNECT_SHEET.md](CONNECT_SHEET.md). The process map is [TOPOLOGY.md](TOPOLOGY.md).

Loan book:

```json
{
  "host": "127.0.0.1",
  "port": "55432",
  "username": "lms_ro",
  "password": "lms_ro_dev",
  "database": "aarohan_lms",
  "schema": "lms",
  "dbtype": "postgres"
}
```

Do not reuse that blob for the ledger. The ledger is port `55434`, user `gl_ro`. Collections are `55433` / `coll_ro`. The vault is `55435` / `gold_ro`.

Passwords in this repository are lab fixtures.

Read the schema from each source yourself. This lab does not extract it for you.

## 3. Join in your product

Do not copy payment rows into the loan book. Do not load partner files into Postgres and call that the source. Optional foreign-data wrappers live in `sql/90_fdw_optional.sql` for a single session that still names two databases. They are off by default.

## Other transports

| Kind | Where | Notes |
|---|---|---|
| ERP and CRM | `http://127.0.0.1:18080` | `Authorization: Bearer aarohan-dev`. Cursor pagination. Missing bearer is 401. `erp-500` returns 500. |
| Events | `http://127.0.0.1:18081` | Pull only. `POST /advance?days=1` moves the clock. The lab does not POST to you. |
| Partner files | `output/landing/` and MinIO | Bucket `aarohan-landing`. Access key `aarohan`, secret `aarohan-minio-dev`. |
| Archive bucket | same endpoint, bucket `archive` | Empty. For a client that wants a second bucket. Not a source system. |
| Mail | SMTP `127.0.0.1:18025` | Inbox UI at `http://127.0.0.1:18084`. |
| Webhook sink | `POST http://127.0.0.1:18083/slack` | Inbound. `GET /inbox` shows what arrived. |

```bash
python3 scripts/connections.py
```

prints these client connections. It does not insert them anywhere.

## Checklist

1. Use the health page for ports. Do not invent them.
2. One connection per source. Do not merge databases.
3. Money is `numeric(19,4)`. Compute it in code, not in a model.
4. Collection efficiency uses the payment feed’s value date. The loan book’s applied cash hides the unpaid-looking loan that the bank already collected.
5. If a source is down, say it is down. A zero is a lie.
