"""Per-source Postgres targets. Loader uses service DNS; clients use published ports.

S1 / S4 / S5 / S8 are dedicated processes. S2 / S3 / S6 / S7 / S9 share the
archive cluster as an *internal* copy — not the client path.
"""

from __future__ import annotations

import os
import time

# Loader / verify (inside compose). Dev passwords are not secrets.
ADMIN_USER = os.environ.get("PG_USER", "aarohan")
ADMIN_PASSWORD = os.environ.get("PG_PASSWORD", "aarohan")

CLUSTERS = {
    "lms": {
        "service": "postgres-lms",
        "host_env": "PG_HOST_LMS",
        "default_host": "postgres-lms",
        "published_port": 55432,  # via pgproxy; lms-slow applies here only
        "via_proxy": True,
    },
    "coll": {
        "service": "postgres-coll",
        "host_env": "PG_HOST_COLL",
        "default_host": "postgres-coll",
        "published_port": 55433,
        "via_proxy": False,
    },
    "gold": {
        "service": "postgres-gold",
        "host_env": "PG_HOST_GOLD",
        "default_host": "postgres-gold",
        "published_port": 55435,
        "via_proxy": False,
    },
    "gl": {
        "service": "postgres-gl",
        "host_env": "PG_HOST_GL",
        "default_host": "postgres-gl",
        "published_port": 55434,
        "via_proxy": False,
    },
    "archive": {
        "service": "postgres-archive",
        "host_env": "PG_HOST_ARCHIVE",
        "default_host": "postgres-archive",
        "published_port": 55436,
        "via_proxy": False,
    },
}

# client=True → this is the connection a product should open.
# client=False → internal archive; catalog must not sell it as the source.
SOURCES = {
    "lms": {
        "id": "s1-lms",
        "dbname": "aarohan_lms",
        "schema": "lms",
        "cluster": "lms",
        "ro_user": "lms_ro",
        "ro_password": "lms_ro_dev",
        "client": True,
    },
    "pay": {
        "id": "s2-pay",
        "dbname": "aarohan_pay",
        "schema": "pay",
        "cluster": "archive",
        "ro_user": "pay_ro",
        "ro_password": "pay_ro_dev",
        "client": False,
    },
    "bureau": {
        "id": "s3-bureau",
        "dbname": "aarohan_bureau",
        "schema": "bureau",
        "cluster": "archive",
        "ro_user": "bureau_ro",
        "ro_password": "bureau_ro_dev",
        "client": False,
    },
    "coll": {
        "id": "s4-coll",
        "dbname": "aarohan_coll",
        "schema": "coll",
        "cluster": "coll",
        "ro_user": "coll_ro",
        "ro_password": "coll_ro_dev",
        "client": True,
    },
    "gold": {
        "id": "s5-gold",
        "dbname": "aarohan_gold",
        "schema": "gold",
        "cluster": "gold",
        "ro_user": "gold_ro",
        "ro_password": "gold_ro_dev",
        "client": True,
    },
    "veh": {
        "id": "s6-vehicle",
        "dbname": "aarohan_veh",
        "schema": "veh",
        "cluster": "archive",
        "ro_user": "veh_ro",
        "ro_password": "veh_ro_dev",
        "client": False,
    },
    "crm": {
        "id": "s7-crm",
        "dbname": "aarohan_crm",
        "schema": "crm",
        "cluster": "archive",
        "ro_user": "crm_ro",
        "ro_password": "crm_ro_dev",
        "client": False,
    },
    "gl": {
        "id": "s8-gl",
        "dbname": "aarohan_gl",
        "schema": "gl",
        "cluster": "gl",
        "ro_user": "gl_ro",
        "ro_password": "gl_ro_dev",
        "client": True,
    },
    "masters": {
        "id": "s9-masters",
        "dbname": "aarohan_masters",
        "schema": "masters",
        "cluster": "archive",
        "ro_user": "masters_ro",
        "ro_password": "masters_ro_dev",
        "client": False,
    },
}

# Back-compat name → dbname map used by older call sites.
DATABASES = {key: spec["dbname"] for key, spec in SOURCES.items()}


def _cluster_host(cluster_key: str) -> str:
    cluster = CLUSTERS[cluster_key]
    return os.environ.get(cluster["host_env"], cluster["default_host"])


def target(source_key: str, *, from_host: bool = False, role: str = "admin") -> dict:
    """Return libpq fields for a source.

    role=admin → aarohan (loader). role=ro → per-source read-only client.
    from_host=True → 127.0.0.1 + published port (scripts on the laptop / box).
    """
    spec = SOURCES[source_key]
    cluster = CLUSTERS[spec["cluster"]]
    if role == "ro":
        user, password = spec["ro_user"], spec["ro_password"]
    else:
        user, password = ADMIN_USER, ADMIN_PASSWORD
    if from_host:
        host, port = "127.0.0.1", cluster["published_port"]
    else:
        host, port = _cluster_host(spec["cluster"]), 5432
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": spec["dbname"],
        "schema": spec["schema"],
        "cluster": spec["cluster"],
        "service": cluster["service"],
        "client": spec["client"],
        "source": source_key,
    }


def connect_source(source_key: str, *, from_host: bool = False, role: str = "admin", dbname: str | None = None):
    import psycopg2

    t = target(source_key, from_host=from_host, role=role)
    return psycopg2.connect(
        host=t["host"],
        port=t["port"],
        user=t["user"],
        password=t["password"],
        dbname=dbname or t["dbname"],
    )


def connect_cluster_admin(cluster_key: str, dbname: str = "postgres"):
    import psycopg2

    cluster = CLUSTERS[cluster_key]
    return psycopg2.connect(
        host=_cluster_host(cluster_key),
        port=5432,
        user=ADMIN_USER,
        password=ADMIN_PASSWORD,
        dbname=dbname,
    )


def wait_all(timeout: int = 180) -> None:
    deadline = time.time() + timeout
    last = None
    pending = set(CLUSTERS)
    while pending and time.time() < deadline:
        ready = set()
        for key in pending:
            try:
                conn = connect_cluster_admin(key)
                conn.close()
                ready.add(key)
            except Exception as exc:  # noqa: BLE001
                last = f"{key}: {exc}"
        pending -= ready
        if pending:
            time.sleep(1)
    if pending:
        raise SystemExit(f"postgres not ready ({', '.join(sorted(pending))}): {last}")


def dsn_line(source_key: str, *, from_host: bool = True, role: str = "ro") -> str:
    t = target(source_key, from_host=from_host, role=role)
    kind = "client" if t["client"] and role == "ro" else "archive"
    return (
        f"{source_key:8} {kind:7} "
        f"postgresql://{t['user']}:{t['password']}@{t['host']}:{t['port']}/{t['dbname']} "
        f"schema={t['schema']}"
    )
