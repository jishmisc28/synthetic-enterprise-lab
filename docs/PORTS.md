# Synthetic Enterprise Lab published ports

Compose publishes every listed port on **`0.0.0.0` and `[::]`**. Nothing is bound to `127.0.0.1` only. A laptop SSH tunnel should forward the rows you need; do not assume localhost-only.

Postgres **5432 inside each database container is not published**, except where the table says so. LMS is reached through the delay proxy.

| Port | Bind | Process | What a client uses it for |
|---|---|---|---|
| 55432 | 0.0.0.0 | `pgproxy` → `postgres-lms:5432` | **S1 LMS** (`lms_ro` / `lms_ro_dev`, db `aarohan_lms`). `lms-slow` applies here only. |
| 55433 | 0.0.0.0 | `postgres-coll` | **S4 Collections** (`coll_ro` / `coll_ro_dev`, db `aarohan_coll`) |
| 55434 | 0.0.0.0 | `postgres-gl` | **S8 GL** (`gl_ro` / `gl_ro_dev`, db `aarohan_gl`) |
| 55435 | 0.0.0.0 | `postgres-gold` | **S5 Gold vault** (`gold_ro` / `gold_ro_dev`, db `aarohan_gold`) |
| 55436 | 0.0.0.0 | `postgres-archive` | Internal archives only: `aarohan_pay`, `aarohan_bureau`, `aarohan_veh`, `aarohan_crm`, `aarohan_masters`. Not the client path for those sources. |
| 18080 | 0.0.0.0 | `erp` | S8 ERP (`/gl/journals`, `/masters/*`) and **S7 CRM** (`/crm/accounts`, `/crm/campaigns`). Bearer `aarohan-dev`. |
| 18081 | 0.0.0.0 | `events` | S2 events **pull**. GET `/payments` `/collections` `/clickstream`. POST `/advance`. No push to a client. |
| 18082 | 0.0.0.0 | `verify` | Health page, `/catalog`, `/verify` |
| 18083 | 0.0.0.0 | `webhook` | Inbound Slack-shaped sink. Not Aarohan events. |
| 18025 | 0.0.0.0 | `mailpit` SMTP | Case mail catcher |
| 18084 | 0.0.0.0 | `mailpit` UI | Inbox |
| 19000 | 0.0.0.0 | `minio` S3 | Client path for S2/S3/S6/S9. Bucket `aarohan-landing`. |
| 19001 | 0.0.0.0 | `minio` console | Browser UI |

Laptop tunnel minimum: `55432`, `55433`, `55434`, `55435`, `18080`, `18081`, `18082`, `19000`.

`make down` is `docker compose down -v` and **destroys** volumes `pgdata-lms`, `pgdata-coll`, `pgdata-gold`, `pgdata-gl`, `pgdata-archive`, `minio`. A reboot without `-v` keeps them. Terminating the instance destroys them.

Backup (on the Docker host):

```bash
cd synthetic-enterprise-lab
docker compose --profile minio exec -T postgres-lms pg_dump -U aarohan aarohan_lms > backup-lms.sql
docker compose --profile minio exec -T postgres-coll pg_dump -U aarohan aarohan_coll > backup-coll.sql
docker compose --profile minio exec -T postgres-gold pg_dump -U aarohan aarohan_gold > backup-gold.sql
docker compose --profile minio exec -T postgres-gl pg_dump -U aarohan aarohan_gl > backup-gl.sql
docker compose --profile minio exec -T postgres-archive pg_dumpall -U aarohan > backup-archive.sql
```
