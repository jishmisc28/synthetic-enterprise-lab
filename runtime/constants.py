"""Dev-only stack constants. These are not secrets."""

from __future__ import annotations

AUTH_BEARER = "aarohan-dev"
PG_USER = "aarohan"
PG_PASSWORD = "aarohan"
# Legacy single-host defaults. Prefer runtime.pg.target().
PG_HOST = "postgres-lms"
PG_PORT = 5432

from runtime.pg import DATABASES  # noqa: E402 — one map, used by load/verify

LANDING_BUCKET = "aarohan-landing"
ARCHIVE_BUCKET = "archive"
CHAOS_PATH = "/data/output/aarohan/stack/chaos.json"
CLOCK_PATH = "/data/output/aarohan/stack/clock.json"
RELATIONSHIPS_PATH = "/data/output/aarohan/stack/relationships.json"
