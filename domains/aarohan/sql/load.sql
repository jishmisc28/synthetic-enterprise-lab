-- Load S1 CSVs into an empty Postgres. File sources stay files / stack services.
-- Run against the generated estate under output/aarohan/ (or set ON_ERROR_STOP).
-- Valid psql: \copy ... FROM 'relative/path' CSV HEADER

\set ON_ERROR_STOP on

-- Dimensions first (FK parents).
\copy lms.product (product_code, name, family, annual_rate, min_p, max_p) FROM 'lms/product.csv' CSV HEADER
\copy lms.branch (branch_id, branch_code, branch_name, state, region, gold_counter, is_digital, bm_email, effective_to, superseded_by) FROM 'lms/branch.csv' CSV HEADER
\copy lms.dealer (dealer_code, name, city, region) FROM 'lms/dealer.csv' CSV HEADER
\copy lms.agent (agent_code, name, region, agency_code, mgr_email, effective_from, effective_to, home_branch) FROM 'lms/agent.csv' CSV HEADER
\copy lms.customer (cif, legal_name, pan, mobile, branch_code, dob) FROM 'lms/customer.csv' CSV HEADER
\copy lms.kyc (kyc_id, cif, pan, aadhaar_last4, status, verified_at) FROM 'lms/kyc.csv' CSV HEADER
\copy lms.application (appl_no, cif, product_code, applied_on, amount) FROM 'lms/application.csv' CSV HEADER
\copy lms.bureau_pull (enquiry_ref, appl_no, cif, score, pulled_on) FROM 'lms/bureau_pull.csv' CSV HEADER
\copy lms.credit_decision (appl_no, decided_on, outcome, score_used, override_flag, loan_no, override_by) FROM 'lms/credit_decision.csv' CSV HEADER
\copy lms.loan_account (loan_no, cif, product_code, branch_code, principal, outstanding_principal, annual_rate, tenor_m, start_date, status, dpd, npa_flag, parent_loan_no, dealer_code, rm_id) FROM 'lms/loan_account.csv' CSV HEADER
\copy lms.disbursement (disb_no, loan_no, amount, disb_date, seq, is_topup) FROM 'lms/disbursement.csv' CSV HEADER
\copy lms.repayment_schedule (schedule_id, loan_no, version, effective_from, emi_amount, tenor_m) FROM 'lms/repayment_schedule.csv' CSV HEADER
\copy lms.instalment (instalment_id, loan_no, due_date, amount, status, principal_due, interest_due, charge_due) FROM 'lms/instalment.csv' CSV HEADER
\copy lms.charge (charge_no, loan_no, reason, amount, event_date, posted_at, due_date) FROM 'lms/charge.csv' CSV HEADER
\copy lms.waiver (waiver_id, charge_no, amount, posted_at) FROM 'lms/waiver.csv' CSV HEADER
\copy lms.payment_applied (lms_receipt_no, loan_no, amount, value_date, posted_at, ext_txn_ref) FROM 'lms/payment_applied.csv' CSV HEADER
\copy lms.payment_allocation (lms_receipt_no, seq, component, amount) FROM 'lms/payment_allocation.csv' CSV HEADER
\copy lms.moratorium (loan_no, start_date, end_date, course_end, grace_months) FROM 'lms/moratorium.csv' CSV HEADER
\copy lms.restructure (loan_no, effective_from, reason) FROM 'lms/restructure.csv' CSV HEADER
\copy lms.write_off (wo_no, loan_no, amount, posted_date, dpd_at, approval_ref) FROM 'lms/write_off.csv' CSV HEADER
\copy lms.recovery (rec_no, loan_no, amount, value_date, reason) FROM 'lms/recovery.csv' CSV HEADER
\copy lms.gold_pledge (pledge_no, loan_no, gross_g, net_g, purity, assessed_inr) FROM 'lms/gold_pledge.csv' CSV HEADER
\copy lms.vehicle_asset (loan_no, vin, dealer_code) FROM 'lms/vehicle_asset.csv' CSV HEADER
\copy lms.insurance_sale (ins_id, loan_no, product, premium, sold_on) FROM 'lms/insurance_sale.csv' CSV HEADER
-- Typed truth for dated rules. Same payload as files/masters/rule_set.json.
\copy lms.rule_set (rule_code, product_code, effective_from, effective_to, payload) FROM 'lms/rule_set.csv' CSV HEADER

-- Do not COPY payments into lms. That collapses the recon.
-- S2–S9 are loaded by Synthetic Enterprise Lab into their own databases / HTTP services.
