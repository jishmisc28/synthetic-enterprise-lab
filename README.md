# Synthetic Enterprise Lab

A local synthetic company whose systems disagree, for testing data agents, analytics, and reconciliation.

A zip of CSVs cannot return HTTP 500, arrive late, or go down. This lab can. You start it, then point your own product at the ports. 

## Show me

Aarohan is the first domain: a lender whose books do not match.

Loan `AF-LN-I01-PL` is the short version.

| System | What it says |
|---|---|
| Payments | UPI `UPI-I01-8891` succeeded for `6052.1400` on 2026-08-03 |
| Loan book | That payment was never applied |
| General ledger | The same amount posted on 2026-08-04, with an empty loan reference |

Same-day loan-book versus ledger is often timing, not a break. This one is a break. `make verify` checks the lab’s own truth sheet, including this case. If the numbers do not match, the pack is wrong.

## Run it

Requirements: Docker, Docker Compose, Make, Python 3.11+.

```bash
git clone https://github.com/jishmisc28/synthetic-enterprise-lab.git
cd synthetic-enterprise-lab
make test          # no Docker
make up            # first build is the slow step
```

Then open http://127.0.0.1:18082/ and run:

```bash
make verify
make break minio-down
make heal
make down          # stops the stack and deletes its volumes
```

`make verify` exits 0 when the loaded estate matches `domains/aarohan/expected/tiny/verification.json`. The health page is the live list of sources. Believe that page for ports.

Generate the domain without Docker:

```bash
PYTHONPATH=domains python3 -c "from aarohan.run import generate; generate('tiny', 20260907, __import__('pathlib').Path('output/aarohan'))"
```

`output/` is generated. It is not part of the git tree.

## Install

There is no package to publish. Clone the repository and use Make. Python dependencies for the services are in `requirements.txt` and are installed inside the image on `make up`. Unit tests use the standard library plus those imports that the tests load; `make test` is the check that does not need Docker.

## Smallest connection

After `make up`, the loan book is Postgres:

```text
host=127.0.0.1 port=55432 dbname=aarohan_lms user=lms_ro password=lms_ro_dev
```

That password is a lab fixture. It is not a credential for any real system. The full sheet is [docs/CONNECT_SHEET.md](docs/CONNECT_SHEET.md).

```bash
python3 scripts/connections.py
```

prints the client connections as JSON. It does not write to any product.

## Architecture

```text
domain generator (seed 20260907)
        │
        ▼
loader
        ├── postgres-lms      :55432   loan book
        ├── postgres-coll     :55433   collections
        ├── postgres-gl       :55434   general ledger
        ├── postgres-gold     :55435   vault
        ├── postgres-archive  :55436   internal copies, not the client path
        ├── erp HTTP          :18080   ledger API and CRM
        ├── events HTTP       :18081   pull only; POST /advance moves the clock
        ├── health            :18082   catalog, verify
        ├── webhook sink      :18083   Slack-shaped inbox
        ├── mailpit           :18025 / :18084
        └── MinIO             :19000   partner files
```

One process per protocol. Four systems of record have their own Postgres process. Payments, bureau, dealer files, and masters are files or HTTP. A Postgres archive of those feeds exists so the verifier can count rows. Do not connect your product to that archive and call it the source.

`make break` can stall the loan-book proxy (`lms-slow`), withhold two days of payment events (`s2-late`), stop MinIO (`minio-down`), or force the ERP to return 500 (`erp-500`). `make heal` puts them back.

Details: [docs/TOPOLOGY.md](docs/TOPOLOGY.md), [docs/PORTS.md](docs/PORTS.md), [docs/DATA_AND_MESSINESS.md](docs/DATA_AND_MESSINESS.md).

## Why it exists

Cross-system work is where analytics and agents fail: two clocks, a file that is not UTF-8, an identity that is a hint rather than a foreign key, a source that is down. A single database cannot host that test. This lab is the other end of the cable.

## What this is not

- Not a warehouse, a metric engine, or an agent framework.
- Not a benchmark leaderboard. The truth sheet checks the fixture. It does not score your model.
- Not a real lender. Aarohan, its people, and its loans are synthetic.
- Not a promise of more industries. One domain ships. Another domain belongs in `domains/<name>/` when it has a generator, a truth sheet, and a disagreement. See [domains/README.md](domains/README.md).

## Limitations

- The first `make up` builds an image and loads the tiny estate. Budget several minutes, not five seconds.
- Ports bind on all interfaces. Do not expose this machine to a network you do not trust. See [SECURITY.md](SECURITY.md).
- `make down` deletes volumes. Generated files under `output/` remain until you delete them.
- This repository’s unit tests do not start Docker. A green `make test` is not a green `make verify`.
- Dev passwords and the bearer token `aarohan-dev` are published on purpose. Rotate nothing: they are not used anywhere else.

## Roadmap

The kernel stays one compose file and one set of commands: `make up`, `make verify`, `make down`. The next useful change is another domain folder, or a fix to a truth-sheet number that the tests can prove. New protocols wait until a domain needs them.

## Contributing

Bugs, wrong truth-sheet numbers, and doc drift are welcome. A new industry is not accepted until this one runs for someone other than the author. [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0. See [LICENSE](LICENSE).
