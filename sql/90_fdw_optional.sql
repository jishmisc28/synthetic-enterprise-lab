-- OPTIONAL. Do not run in `make up`.
-- Cross-source SQL in one session without copying rows.
-- Connect to aarohan_lms as aarohan, then:
--
--   psql -h 127.0.0.1 -p 55432 -U aarohan -d aarohan_lms -f sql/90_fdw_optional.sql
--
-- Leave this off unless one SQL session must name two databases.
-- It does not copy rows, and it is not how a client should connect.

CREATE EXTENSION IF NOT EXISTS postgres_fdw;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_foreign_server WHERE srvname = 'aarohan_pay') THEN
        CREATE SERVER aarohan_pay FOREIGN DATA WRAPPER postgres_fdw
            OPTIONS (host 'postgres-archive', dbname 'aarohan_pay');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_foreign_server WHERE srvname = 'aarohan_gl') THEN
        CREATE SERVER aarohan_gl FOREIGN DATA WRAPPER postgres_fdw
            OPTIONS (host 'postgres-gl', dbname 'aarohan_gl');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_foreign_server WHERE srvname = 'aarohan_gold') THEN
        CREATE SERVER aarohan_gold FOREIGN DATA WRAPPER postgres_fdw
            OPTIONS (host 'postgres-gold', dbname 'aarohan_gold');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_foreign_server WHERE srvname = 'aarohan_coll') THEN
        CREATE SERVER aarohan_coll FOREIGN DATA WRAPPER postgres_fdw
            OPTIONS (host 'postgres-coll', dbname 'aarohan_coll');
    END IF;
END$$;

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER SERVER aarohan_pay
    OPTIONS (user 'aarohan', password 'aarohan');
CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER SERVER aarohan_gl
    OPTIONS (user 'aarohan', password 'aarohan');
CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER SERVER aarohan_gold
    OPTIONS (user 'aarohan', password 'aarohan');
CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER SERVER aarohan_coll
    OPTIONS (user 'aarohan', password 'aarohan');

CREATE SCHEMA IF NOT EXISTS pay_fdw;
CREATE SCHEMA IF NOT EXISTS gl_fdw;
CREATE SCHEMA IF NOT EXISTS gold_fdw;
CREATE SCHEMA IF NOT EXISTS coll_fdw;

IMPORT FOREIGN SCHEMA pay FROM SERVER aarohan_pay INTO pay_fdw;
IMPORT FOREIGN SCHEMA gl FROM SERVER aarohan_gl INTO gl_fdw;
IMPORT FOREIGN SCHEMA gold FROM SERVER aarohan_gold INTO gold_fdw;
IMPORT FOREIGN SCHEMA coll FROM SERVER aarohan_coll INTO coll_fdw;

-- Example (K5 uses S2, not LMS applied):
-- SELECT (SELECT COALESCE(SUM(amount),0) FROM pay_fdw.payment
--           WHERE status = 'SUCCESS'
--             AND value_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31')
--        /
--        NULLIF((SELECT COALESCE(SUM(amount),0) FROM lms.instalment
--           WHERE due_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'), 0);
