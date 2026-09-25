-- Management metrics. Close = 2026-08-31. Money numeric(19,4) INR.
-- Definitions live with the domain generator and docs/DATA_AND_MESSINESS.md.

CREATE SCHEMA IF NOT EXISTS metric;

-- K1 disbursement in period (use the close month unless overridden)
CREATE OR REPLACE VIEW metric.k1_disbursement AS
SELECT COALESCE(SUM(d.amount), 0)::numeric(19,4) AS value
FROM lms.disbursement d
WHERE d.disb_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31';

-- K2 book (live outstanding)
CREATE OR REPLACE VIEW metric.k2_aum AS
SELECT COALESCE(SUM(COALESCE(l.outstanding_principal, l.principal)), 0)::numeric(19,4) AS value
FROM lms.loan_account l
WHERE l.status NOT IN ('CLOSED', 'SETTLED', 'WRITTEN_OFF');

-- K5 collection efficiency uses S2 value_date, not LMS applied (hides I01 if you use LMS).
-- Load files/payments/*.csv as stage.s2_payment before this view is honest.

-- K12 gold LTV-breach count must use GOLD_LTV as-of valuation_date, not the current cap.
-- K13 recon break count excludes timing_not_break (GL T+1).
