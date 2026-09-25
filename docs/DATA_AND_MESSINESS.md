# Data model, joins, KPIs, and why the data is messy

This document is the **reasoning**. Table-by-table DDL for the first domain is in [`../domains/aarohan/`](../domains/aarohan/). Synthetic Enterprise Lab as a lab does not invent a second set of numbers — the domain generator is the only writer of truth.

Read this after [`../README.md`](../README.md) and [`CONNECT.md`](CONNECT.md). An agent building KPIs should not skip the join-key and messiness sections.

## Why several sources, not one warehouse

A real customer does not have one clean schema. They have an LMS, a bank feed, a bureau file, a vault system, a GL, a CRM, and a folder of partner Excel. Those systems **disagree**. The product is judged on whether it can say so.

So Synthetic Enterprise Lab keeps them as **separate processes**. A silent SQL join across schemas would fake the demo. Optional FDW (`sql/90_fdw_optional.sql`) is for one SQL session that still **names** the two databases — never a dump-and-load.

## Generic model (any domain)

Each domain still has:

1. **A system of record** (typed Postgres). Money is `numeric(19,4)`. Dates are dates.
2. **A cash or movement feed** that is *not* a table inside (1).
3. **At least one file-shaped partner** (Excel, gzip, fixed-width, a non-UTF-8 encoding).
4. **Identity that does not line up** — same human, two keys, or one key used two ways.
5. **A clock that can disagree** — when it happened vs when it was posted vs when we saw it.
6. **Dated rules** — today’s policy on yesterday’s event is a bug.
7. **A truth sheet** (`verification.json`, `ground_truth.json`) the health/verify API can repeat.

Add a domain by adding `domains/<name>/` with a generator and a catalog row. Do not fork the runtime. See [`../domains/README.md`](../domains/README.md).

---

## Aarohan (fintech) — the first domain

Indian multi-product NBFC (personal loan, BNPL, two-wheeler, used vehicle, education, gold). Window 2024-09-01 → 2026-08-31. Close **2026-08-31**. Seed **20260907**.

One CIF may hold several products. A top-up is a **new** `loan_no` pointing at `parent_loan_no`.

### Lifecycle (LMS)

```
application → KYC → bureau → decision → sanction → disbursement → schedule
       ↘ rejected    ↘ cancelled              ↘ partial disbursement
                                                    │
                         instalment ←── moratorium / restructure / reschedule
                                                    │
                         payment (partial | full | prepay | NACH fail)
                                                    │
                         DPD / SMA / NPA → collection → PTP / visit / agency
                                                    │
                    current │ settlement │ foreclosure │ repossession
                            │ write-off → recovery-after-WO
                            │ gold: reval / top-up / auction / release
                            └ closure
```

### Sources and grain

| Id | Source | Kind | Grain | Identity |
|---|---|---|---|---|
| S1 | LMS Postgres `lms` | postgres | loan, customer, charge, rule | `cif`, `loan_no` |
| S2 | Payments (Postgres + events) | postgres + events | one gateway / till event | `txn_ref` / `utr` |
| S3 | Bureau | postgres + files | PAN as-of | `pan` + `reported_as_of` |
| S4 | Collections | postgres + files | attempt / PTP | `event_id` |
| S5 | Gold vault | postgres | packet | `packet_id` + `kind` |
| S6 | Dealer | postgres + files | commission | `commission_id` |
| S7 | CRM | saas | account / offer | `AccountNumber`, `offer_id` |
| S8 | GL / ERP | postgres + erp | journal line | `je_id` |
| S9 | Masters | postgres | versioned row | natural key + `effective_from` |

`lms.gold_pledge` is an LMS **copy**. Vault custody (`custody_state`) lives only on S5. Payments are not `lms.payment_applied`.

Dated rules have **one typed home**: `lms.rule_set.payload` (jsonb). The JSON file is the same 31 rows for humans. A load that leaves `lms.rule_set` empty is a failed pack.

### S1 LMS entities (typed)

| Entity | Grain | Natural key | Notes |
|---|---|---|---|
| `branch` | one branch (or DIGITAL) | `branch_code` | SCD2 rename in S9 |
| `product` | one offer | `product_code` | FK parent — must load first |
| `customer` | one CIF | `cif` `AF-########` | Twins share a PAN, not a PK |
| `loan_account` | one contract | `loan_no` | `npa_flag` NOT NULL; `parent_loan_no` is convention |
| `disbursement` | one tranche | `disb_no` | K1 sums this, not sanctioned |
| `instalment` | one due | `(loan_id, due_date, schedule_version)` | K5 denominator |
| `charge` / `waiver` | one fee | `charge_no` | Dated rule authorises it |
| `payment_applied` | LMS’s view of a receipt | `lms_receipt_no` | `ext_txn_ref` is **not** an FK to S2 |
| `gold_pledge` | LMS copy of a pledge | `pledge_no` | Weights here are not vault truth |
| `rule_set` | one dated rule row | `(rule_code, product_code, effective_from)` | `payload` jsonb |

Full DDL: `domains/aarohan/sql/00_lms_schema.sql`.

---

## Join keys (conventions, not foreign keys)

Nothing across sources is an FK. Exact unmatched counts after load: `GET /relationships` or the health page.

| Left | Right | Key | Enforced? | What is left unmatched on purpose |
|---|---|---|---|---|
| S2 | S1 applied | `utr\|txn_ref` = `ext_txn_ref` | no | Bank SUCCESS the LMS never applied (I01). Tiny: **4 of 202**, including `UPI-I01-8891`. |
| S2 | S1 loan | `loan_hint` = `loan_no` | no | Blank hint on cash tills |
| S3 | S1 customer | **PAN** | no | CIF twins: one PAN, two CIFs |
| S3 | S1 customer | `cif_hint` | no | Hint only |
| S4 | S1 loan | `loan_ref` | no | Walk-in with no ref |
| S5 | S1 pledge | `pledge_no` | no | Packets with no pledge |
| S6 | S1 loan | `loan_no` | no | Commission on a bad loan (I07) |
| S7 | S1 customer | `cif_hint` | no | Hint. `AccountNumber` is the CRM key |
| S8 | S1 loan | `loan_ref` | no | Sparse on `CASH_BATCH` (I01’s GL line is empty) |
| S9 | S1 customer | PAN → two CIFs | no | Twins are not a primary-key collision |

CIF twins example: `AF-00010001` and `AF-00020001`, PAN `AHWPK1111A`.

### Why analysis has to join (and where it must not)

- **K5 collection efficiency** needs S1 instalments **and** S2 `value_date`. LMS applied hides I01.
- **K12 gold LTV** needs S5 valuation **and** the dated GOLD_LTV rule. Today’s cap on an old pledge is wrong.
- **K13 recon** needs S1 + S2 + S8. Same-day LMS vs GL is `timing_not_break`, not a case.
- **K14 PTP kept** needs S4 **and** S2 money. A PTP “kept” with no bank row is empty calories.
- Do **not** join S2 into `lms` “to make the SQL shorter”. That deletes the disagreement.

---

## Why KPIs exist (Aarohan)

KPIs are **management questions**, not decorations. Each one can be lied about if you pick the wrong source. Money is `numeric(19,4)` in SQL. A language model must not invent amounts.

| Id | Question | Honest source | Easy lie |
|---|---|---|---|
| K1 | What did we disburse this close month? | `lms.disbursement` | Counting sanctioned, not disbursed |
| K2 | What is the live book? | outstanding on live loans | Treating written-off as live; using sanction amount |
| K3 | What did we earn? | LMS interest + fee; GL as a **check** | GL cash interest |
| K4 | Fee leakage | charges that fail the dated rule | All waivers as leakage |
| K5 | Collection efficiency | **S2** SUCCESS / instalments due | Using LMS applied — hides I01 |
| K6 | 90+ rate | DPD≥90 AUM / AUM | Count of loans, not AUM |
| K7 | Roll 0→1 | DPD movement by product | Using status, not DPD |
| K8 | GNPA | NPA outstanding / AUM | Mixing write-off back in |
| K9 | Write-off | SUM(wo) in period | Residuals < ₹500 as “losses” |
| K10 | Recovery rate | S2-dated recoveries / WO stock | Recovery posted to the wrong loan (I15) |
| K11 | Contribution by product | LMS + GL + dealer + incentive | Ignoring gold auction surplus |
| K12 | Gold LTV breaches | S5 valuation vs **dated** GOLD_LTV | Using today’s cap on an old pledge |
| K13 | Recon breaks | M10 keys except `timing_not_break` | Calling GL T+1 a break |
| K14 | PTP kept rate | S4 kinds **with S2 money** | PTP kept without a bank row |

K5, K10, K11, K12, K13, K14 cannot be answered honestly from the LMS alone.

Monitors (M1–M10) are the cases a control function should open. Near-misses must **not** fire. Full list: health `GET /expect/monitor/M7` and `domains/aarohan/expected/tiny/verification.json`.

Reviews consume metric ids: daily exception worklist (IM tiles), weekly lending/collections, monthly pack, credit/risk, gold ops. The tile is not the case.

---

## Time model

| Clock | Meaning |
|---|---|
| `event_date` | When it happened (payment initiated, visit made, gold weighed) |
| `value_date` | When it counts for interest / DPD (NACH settlement, not presentment) |
| `posted_at` / `ingested_at` | When this system recorded it |
| `effective_from` / `effective_to` | Which rule or master version applies |

NACH is often D−1 / D+1. IST is the business calendar. Gateway timestamps on the payment file are UTC. That difference is seeded.

`POST /advance` moves the **world** clock. Partner file waves also drop on advance.

---

## Messiness that is on purpose

This is not dirty data for show. Each mess matches a real failure mode.

| Mess | Why it exists | What a product must do |
|---|---|---|
| Three clocks on money | Banks and ledgers do not share a clock | Use `value_date` for DPD and K5 |
| GL T+1 for automated cash | Nightly batch | Same-day LMS vs GL is `timing_not_break` |
| Dated rules | Waterfall flips 2025-04-01 (PL/BNPL/EDU). Gold LTV 85% → 75% on 2025-07-01 | As-of join. “Current policy” on an old event is a bug |
| CIF twins | Gold counter opened a new CIF; digital already had one | PAN is the steward. Two CIFs, one PAN — not a PK collision |
| Unmatched UTRs | Money at the bank, overdue on the book (I01) | M1. Do not delete the S2 row |
| Partner files that are not UTF-8 CSV | That is what partners send | Merged Excel headers, TOTAL row, gzip, jsonl, cp1252, fixed-width |
| A source that is down | Object stores and ERPs fail | Say the source is down. A zero is a lie |
| Stale bureau / gold val | Pull at login, decide D+3; no reval job | Score as-of pull; age vs `gold_reval_days` |
| Branch rename / agent transfer | S9 SCD2 | Do not group by name; incentive uses the collecting agent that day |
| Duplicate / missing collections | App double-submit; paper in the field | Absence is not zero activity |
| LMS status lag | Payment not applied | Do not trust `loan_account.status` for cash |

Columns that will be misused:

| Column | Means | Does not mean |
|---|---|---|
| `loan_account.dpd` | LMS’s current DPD | The DPD a payment should have cleared |
| `payment_applied.amount` | What LMS applied | What the bank received |
| `gold_pledge.gross_g` | What the appraiser typed into LMS | Vault scale weight |
| `charge.reason` | The clerk’s reason | The rule that authorised it |
| `write_off.approval_ref` | A string | That an approval exists |
| `gl.loan_ref` | Optional tag | A complete subledger |
| `bureau.score` | Score on `reported_as_of` | Score on sanction date |

---

## What we will not do

- Load payments into the LMS to “make verify easier”.
- Put vault custody on `lms.gold_pledge`.
- Let a language model compute money.
- Copy rows between databases so one metric SQL can see everything.
- Treat CIF twins as a duplicate primary key.
- Redesign incidents I01–I15, near-misses, or dated rules to make a load easier.
