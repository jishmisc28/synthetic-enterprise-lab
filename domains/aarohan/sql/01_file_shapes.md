# Aarohan file / API shapes (S2–S9)

S1 is Postgres `lms` (`00_lms_schema.sql`). Everything below stays a file or JSON feed.

| Source | Path under `output/aarohan/` | Grain | Identity |
|---|---|---|---|
| S2 UPI | `files/payments/upi.csv` | one gateway event | `txn_ref` |
| S2 NACH | `files/payments/nach.csv` | one mandate presentment | `utr` |
| S2 NEFT | `files/payments/neft.csv` | one transfer | `utr` |
| S2 cash | `files/payments/cash.csv` | one branch receipt | `txn_ref` |
| S3 bureau | `files/bureau/bureau_2026-07.csv` | one PAN as-of | `bureau_id` + `reported_as_of` |
| S4 collections | `files/collections/events.csv` | one attempt / PTP / visit | `event_id` |
| S4 incentives | `files/collections/incentives.csv` | one payout | `incentive_id` |
| S5 gold | `files/gold/packets.csv` | one vault event | `packet_id` + kind |
| S6 dealer | `files/vehicle/commissions.csv` | one commission | `commission_id` |
| S7 CRM | `api/accounts.json`, `api/campaigns.json` | account / offer | `AccountNumber`, `offer_id` |
| S8 GL | `files/gl/journals.csv` | one journal line | `je_id` |
| S9 masters | `files/masters/*.csv`, `rule_set.json` | versioned row | natural key + `effective_from` |

Clocks on every money event: `event_date`, `value_date`, `settlement_date` / `posted_at`. They are allowed to disagree. That is the exercise.
