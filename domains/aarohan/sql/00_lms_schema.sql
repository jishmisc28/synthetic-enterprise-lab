-- Aarohan LMS (S1). Payments stay in files. Vault custody stays in S5.
-- A CREATE TABLE for payment_gateway_raw here is a failed pack.
-- lms.gold_pledge must not carry custody_state.

CREATE SCHEMA IF NOT EXISTS lms;

CREATE TABLE lms.branch (
    branch_id           integer PRIMARY KEY,
    branch_code         text NOT NULL UNIQUE,
    branch_name         text NOT NULL,
    state               text NOT NULL,
    region              text NOT NULL,
    gold_counter        boolean NOT NULL,
    is_digital          boolean NOT NULL,
    bm_email            text NOT NULL,
    effective_to        date,                      -- SCD2, null = current
    superseded_by       text
);

CREATE TABLE lms.product (
    product_code        text PRIMARY KEY,
    name                text NOT NULL,
    family              text NOT NULL,
    annual_rate         numeric(19,4) NOT NULL,
    min_p               numeric(19,4),
    max_p               numeric(19,4)
);

CREATE TABLE lms.dealer (
    dealer_code         text PRIMARY KEY,
    name                text NOT NULL,
    city                text NOT NULL,
    region              text NOT NULL
);

CREATE TABLE lms.agent (
    agent_code          text NOT NULL,
    name                text NOT NULL,
    region              text NOT NULL,
    agency_code         text NOT NULL,
    mgr_email           text NOT NULL,
    effective_from      date NOT NULL,
    effective_to        date,
    home_branch         text,
    PRIMARY KEY (agent_code, effective_from)      -- SCD2, A-WEST-07 transfers
);

CREATE TABLE lms.customer (
    cif                 text PRIMARY KEY,          -- AF-########
    legal_name          text NOT NULL,
    pan                 text NOT NULL,
    mobile              text,
    branch_code         text,
    dob                 date
);

CREATE TABLE lms.kyc (
    kyc_id              text PRIMARY KEY,
    cif                 text NOT NULL REFERENCES lms.customer (cif),
    pan                 text NOT NULL,
    aadhaar_last4       text,
    status              text NOT NULL,
    verified_at         date
);

CREATE TABLE lms.application (
    appl_no             text PRIMARY KEY,
    cif                 text NOT NULL REFERENCES lms.customer (cif),
    product_code        text NOT NULL REFERENCES lms.product (product_code),
    applied_on          date NOT NULL,
    amount              numeric(19,4) NOT NULL
);

CREATE TABLE lms.bureau_pull (
    enquiry_ref         text PRIMARY KEY,
    appl_no             text REFERENCES lms.application (appl_no),
    cif                 text,
    score               integer,
    pulled_on           date
    -- Score is a copy. S3 is the bureau.
);

CREATE TABLE lms.credit_decision (
    appl_no             text NOT NULL REFERENCES lms.application (appl_no),
    decided_on          date NOT NULL,
    outcome             text NOT NULL,
    score_used          integer,
    override_flag       boolean NOT NULL DEFAULT false,
    loan_no             text,
    override_by         text,
    PRIMARY KEY (appl_no, decided_on)
);

CREATE TABLE lms.loan_account (
    loan_no             text PRIMARY KEY,          -- AF-LN-…
    cif                 text NOT NULL REFERENCES lms.customer (cif),
    product_code        text NOT NULL REFERENCES lms.product (product_code),
    branch_code         text NOT NULL,
    principal           numeric(19,4) NOT NULL,
    outstanding_principal numeric(19,4),
    annual_rate         numeric(19,4) NOT NULL,
    tenor_m             integer NOT NULL,
    start_date          date NOT NULL,
    status              text NOT NULL,
    dpd                 integer NOT NULL DEFAULT 0,
    npa_flag            boolean NOT NULL DEFAULT false,
    parent_loan_no      text,                      -- convention, top-up
    dealer_code         text,
    rm_id               text
);

CREATE TABLE lms.disbursement (
    disb_no             text PRIMARY KEY,
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    amount              numeric(19,4) NOT NULL,
    disb_date           date NOT NULL,
    seq                 integer NOT NULL,
    is_topup            boolean NOT NULL DEFAULT false
);

CREATE TABLE lms.repayment_schedule (
    schedule_id         text PRIMARY KEY,
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    version             integer NOT NULL,
    effective_from      date NOT NULL,
    emi_amount          numeric(19,4) NOT NULL,
    tenor_m             integer
);

CREATE TABLE lms.instalment (
    instalment_id       text PRIMARY KEY,
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    due_date            date NOT NULL,
    amount              numeric(19,4) NOT NULL,
    status              text NOT NULL,             -- DUE | PAID | PARTIAL | OVERDUE
    principal_due       numeric(19,4) NOT NULL,
    interest_due        numeric(19,4) NOT NULL,
    charge_due          numeric(19,4) NOT NULL
);

CREATE TABLE lms.charge (
    charge_no           text PRIMARY KEY,
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    reason              text NOT NULL,             -- LATE | BOUNCE | PENAL | FEE
    amount              numeric(19,4) NOT NULL,
    event_date          date NOT NULL,
    posted_at           timestamptz,
    due_date            date
);

CREATE TABLE lms.waiver (
    waiver_id           text PRIMARY KEY,
    charge_no           text REFERENCES lms.charge (charge_no),
    amount              numeric(19,4) NOT NULL,
    posted_at           timestamptz
);

CREATE TABLE lms.payment_applied (
    lms_receipt_no      text PRIMARY KEY,
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    amount              numeric(19,4) NOT NULL,
    value_date          date NOT NULL,
    posted_at           timestamptz,
    ext_txn_ref         text                       -- convention to S2, not an FK
);

CREATE TABLE lms.payment_allocation (
    lms_receipt_no      text NOT NULL REFERENCES lms.payment_applied (lms_receipt_no),
    seq                 integer NOT NULL,
    component           text NOT NULL,             -- INTEREST | CHARGE | PRINCIPAL
    amount              numeric(19,4) NOT NULL,
    PRIMARY KEY (lms_receipt_no, seq)
);

CREATE TABLE lms.moratorium (
    loan_no             text PRIMARY KEY REFERENCES lms.loan_account (loan_no),
    start_date          date NOT NULL,
    end_date            date NOT NULL,
    course_end          date,
    grace_months        integer
);

CREATE TABLE lms.restructure (
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    effective_from      date NOT NULL,
    reason              text,
    PRIMARY KEY (loan_no, effective_from)
);

CREATE TABLE lms.write_off (
    wo_no               text PRIMARY KEY,
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    amount              numeric(19,4) NOT NULL,
    posted_date         date NOT NULL,
    dpd_at              integer,
    approval_ref        text                       -- nullable on purpose
);

CREATE TABLE lms.recovery (
    rec_no              text PRIMARY KEY,
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    amount              numeric(19,4) NOT NULL,
    value_date          date NOT NULL,
    reason              text
);

-- LMS copy of the pledge. Weights here are not vault truth.
-- custody_state is owned by S5 (files/gold/packets.csv). Do not add it here.
CREATE TABLE lms.gold_pledge (
    pledge_no           text PRIMARY KEY,
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    gross_g             numeric(12,3) NOT NULL,
    net_g               numeric(12,3) NOT NULL,
    purity              text NOT NULL,
    assessed_inr        numeric(19,4) NOT NULL
);

CREATE TABLE lms.vehicle_asset (
    loan_no             text PRIMARY KEY REFERENCES lms.loan_account (loan_no),
    vin                 text,
    dealer_code         text
);

CREATE TABLE lms.insurance_sale (
    ins_id              text PRIMARY KEY,
    loan_no             text NOT NULL REFERENCES lms.loan_account (loan_no),
    product             text NOT NULL,
    premium             numeric(19,4) NOT NULL,
    sold_on             date
);

CREATE TABLE lms.rule_set (
    rule_code           text NOT NULL,
    product_code        text NOT NULL,
    effective_from      date NOT NULL,
    effective_to        date,
    payload             jsonb NOT NULL,
    PRIMARY KEY (rule_code, product_code, effective_from)
);
