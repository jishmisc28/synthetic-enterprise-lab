# Contributing

Issues and pull requests are welcome for:

- a command in the README that does not match the Makefile
- a truth-sheet number that the generator and `expected/tiny` disagree on
- a port, role, or health check that drifted from `docker-compose.yml`
- a unit test that fails without Docker

## What we will not merge yet

- a second compose file
- a domain that copies Aarohan’s tables and renames them
- a client that calls out to a hosted model to compute money
- a change to named incident keys (`AF-LN-I01-PL` and the rest) so a demo is easier

A new domain needs its own folder under `domains/`, a deterministic generator, a `verification.json`, one cross-source disagreement, and tests that run without Docker. Open an issue before starting one.

## Development

```bash
make test
```

That is the required check. `make up` and `make verify` need Docker and are how you confirm a loader change.

Money stays `numeric(19,4)`, computed in code.

## License

By contributing, you agree that your contributions are licensed under the Apache License 2.0, the same as the rest of the repository.
