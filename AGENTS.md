# Agents

This repository is a synthetic company’s IT. Read it as a system you connect to, not as a product you extend with a hidden app.

1. Read [README.md](README.md), then [docs/CONNECT.md](docs/CONNECT.md) and [docs/TOPOLOGY.md](docs/TOPOLOGY.md).
2. For joins and why the numbers disagree, read [docs/DATA_AND_MESSINESS.md](docs/DATA_AND_MESSINESS.md). Do not invent a second model.
3. `make up`. Open http://127.0.0.1:18082/. That page wins on ports and health. [docs/CONNECT_SHEET.md](docs/CONNECT_SHEET.md) is the same map on paper.
4. One connection per source. Never merge two databases. Never copy the payment feed into the loan book.
5. Money is `numeric(19,4)` in code and SQL. Do not invent amounts. Do not let a model compute money.
6. For Aarohan collection efficiency, use the payment feed’s value date. Applied cash on the loan book hides incident I01.
7. If a source is down, say it is down. A zero is a lie.
8. A new domain is a folder under `domains/` plus catalog rows. Do not fork `runtime/` or add a second compose file. See [domains/README.md](domains/README.md).
9. An HTTP service you add keeps authentication, pagination, and a way to fail.
10. Python under `runtime/`, `scripts/`, and `domains/` must not import an application package (`lib` or `app`).

Aarohan incidents and rules are already decided. Do not redesign them to make a load easier.
