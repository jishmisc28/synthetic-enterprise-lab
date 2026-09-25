# Verification sheet (generated, estate=aarohan, scale=tiny, seed=20260907)

Close: 2026-08-31

## KPIs

| ID | Value | Unit |
|---|---|---|
| K1 | 775500.0000 | inr |
| K2 | 10888000.0000 | inr |
| K3 | 611395.4592 | inr |
| K4 | 500.0000 | inr |
| K5 | 0.8714 | rate |
| K6 | 0.0073 | rate |
| K7 | rows=0 | DM |
| K8 | 0.0073 | rate |
| K9 | 18400.0000 | inr |
| K10 | 2.4804 | rate |
| K11 | rows=4 | DM |
| K12 | 1.0000 | count |
| K13 | 4.0000 | count |
| K14 | 0.6667 | rate |

## Monitors

- **M1** observed 1: `['AF-LN-I01-PL']` (must ['AF-LN-I01-PL']; must not ['AF-LN-I01N-PL'])
- **M2** observed 2: `['CHG-I03', 'INS-I04']` (must ['CHG-I03', 'INS-I04']; must not ['CHG-I03N'])
- **M3** observed 1: `['RCPT-I02']` (must ['RCPT-I02']; must not ['RCPT-I02N'])
- **M4** observed 1: `['AF-LN-M4-EMPTY']` (must ['AF-LN-M4-EMPTY']; must not ['AF-LN-M4-ZERO'])
- **M5** observed 2: `['INC-I05', 'INC-I06']` (must ['INC-I05', 'INC-I06']; must not ['INC-I05N'])
- **M6** observed 2: `['AF-AP-I08', 'AF-AP-I09']` (must ['AF-AP-I08', 'AF-AP-I09']; must not ['AF-AP-I08N'])
- **M7** observed 3: `['PKT-I10', 'PKT-I11', 'PKT-I12']` (must ['PKT-I10', 'PKT-I11', 'PKT-I12']; must not ['PKT-I10N'])
- **M8** observed 3: `['WO-I14', 'PKT-I13', 'REC-I15']` (must ['PKT-I13', 'WO-I14', 'REC-I15']; must not ['WO-I14N'])
- **M9** observed 1: `['CMP-I09']` (must ['CMP-I09']; must not ['CMP-GOLD-OK'])
- **M10** observed 4: `['AF-LN-I15-PL-A', 'AF-LN-I01-PL', 'AF-LN-I13-GL', 'AF-LN-I07-TW']` (must ['AF-LN-I01-PL', 'AF-LN-I13-GL', 'AF-LN-I07-TW']; must not ['timing_not_break'])

## Incidents

Valid: ['I01', 'I02', 'I03', 'I04', 'I05', 'I06', 'I07', 'I08', 'I09', 'I10', 'I11', 'I12', 'I13', 'I14', 'I15', 'M4-EMPTY']
Near-miss: ['I01n', 'I02n', 'I03n', 'I05n', 'I07n', 'I08n', 'I10n', 'I14n', 'M4-ZERO', 'M9-GOLD-OK']

## Cleaning

{
  "customers": 157,
  "loans": 108,
  "instalments": 400,
  "s2_payments": 202,
  "collection_events": 31,
  "gold_ops": 15,
  "gl_lines": 199,
  "identity_twins": 3
}

