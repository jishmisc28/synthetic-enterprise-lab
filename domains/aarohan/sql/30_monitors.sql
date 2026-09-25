-- Ten IM metrics. Identity columns are the dedupe key.
-- Ground truth for these views is domains/aarohan/expected/.
-- These views assume staged file sources: stage.s2_payment, stage.s5_gold, stage.s4_event, stage.s8_gl.

CREATE SCHEMA IF NOT EXISTS monitor;

-- M1 Paid at the bank, overdue at the book. Identity: (txn_ref, loan_no)
CREATE OR REPLACE VIEW monitor.m1_paid_still_overdue AS
SELECT
    p.txn_ref,
    p.loan_hint AS loan_no,
    p.value_date,
    i.instalment_id
FROM stage.s2_payment p
JOIN lms.instalment i
  ON i.loan_no = p.loan_hint
 AND i.status = 'OVERDUE'
LEFT JOIN lms.payment_applied a
  ON a.ext_txn_ref IN (p.utr, p.txn_ref)
WHERE p.status = 'SUCCESS'
  AND p.value_date <= DATE '2026-08-31'
  AND a.lms_receipt_no IS NULL;

-- M2 Incorrect late charge or EMI inside moratorium. Identity: charge_no / instalment_id
CREATE OR REPLACE VIEW monitor.m2_bad_charge AS
SELECT c.charge_no AS identity, c.loan_no, 'LATE_IN_GRACE' AS reason
FROM lms.charge c
JOIN lms.loan_account l ON l.loan_no = c.loan_no
JOIN lms.payment_applied p ON p.loan_no = c.loan_no
JOIN lms.rule_set r
  ON r.rule_code = 'GRACE_DAYS'
 AND r.product_code = l.product_code
 AND r.effective_from <= p.value_date
 AND (r.effective_to IS NULL OR r.effective_to >= p.value_date)
WHERE c.reason = 'LATE'
  AND (p.value_date - c.due_date) <= (r.payload->>'days')::int
UNION ALL
SELECT i.instalment_id, i.loan_no, 'EMI_IN_MORATORIUM'
FROM lms.instalment i
JOIN lms.moratorium m ON m.loan_no = i.loan_no
WHERE i.due_date < m.end_date;

-- M3 Partial payment walked the old waterfall. Identity: lms_receipt_no
CREATE OR REPLACE VIEW monitor.m3_old_waterfall AS
SELECT a.lms_receipt_no
FROM lms.payment_allocation a
JOIN lms.payment_applied p ON p.lms_receipt_no = a.lms_receipt_no
JOIN lms.loan_account l ON l.loan_no = p.loan_no
WHERE a.seq = 1
  AND a.component = 'CHARGE'
  AND p.value_date >= DATE '2025-04-01'
  AND l.product_code IN ('PL', 'BNPL', 'EDU');

-- M4 Motion without money. Identity: loan_no
-- ≥3 attempts in 14 days, DPD≥30, no PTP_KEPT, no S2 success.

-- M5 Incentive without qualifying recovery. Identity: incentive_id
-- Reversal within 7 days or collecting agent ≠ paid agent.

-- M6 Credit policy exception. Identity: appl_no

-- M7 Gold collateral / LTV / release / stale val. Identity: packet_id
-- custody_state comes from stage.s5_gold, never from lms.gold_pledge.

-- M8 Unsupported write-off / recovery. Identity: wo_no | rec_no | packet_id

-- M9 Cross-sell to stressed customer. Identity: offer_id

-- M10 Three-book cash recon. Identity: (value_date, loan_no)
-- Shift GL CASH_BATCH posted_date by -1 day. timing_not_break is listed, not a case.
-- I07 (duplicate dealer commission) is evidence on this monitor, not an 11th IM.
