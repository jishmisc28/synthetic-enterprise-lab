# Security

Synthetic Enterprise Lab is a local fixture. Every password, bearer token, and MinIO key in this repository is a **lab fixture**. They are the same in every clone. Do not point them at a real company, and do not reuse them anywhere else.

The compose file publishes ports on all interfaces, including Postgres, MinIO, and the health API. Run it on a machine you control. Do not put it on a public network.

`make down` deletes the lab’s Docker volumes. It does not touch anything outside this project.

## Reporting a vulnerability

If you find a problem in the lab itself (for example a dependency issue, or a file in git that is not a fixture), open a private report through GitHub: [Security advisories](https://github.com/jishmisc28/synthetic-enterprise-lab/security/advisories/new) for this repository.

Please do not file a public issue for a credential you copied out of the README. Those values are intentional and local.
