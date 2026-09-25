"""Per-source read-only roles. lms_ro cannot CONNECT to aarohan_gl, etc."""

from __future__ import annotations

from psycopg2 import sql

from runtime.pg import ADMIN_USER, CLUSTERS, SOURCES, connect_cluster_admin, connect_source


def _revoke_public_and_grant(cur, dbname: str, ro_user: str) -> None:
    cur.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(dbname)))
    cur.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}, {}").format(
            sql.Identifier(dbname),
            sql.Identifier(ro_user),
            sql.Identifier(ADMIN_USER),
        )
    )


def _ensure_login(cur, user: str, password: str) -> None:
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,))
    if cur.fetchone():
        cur.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD %s").format(sql.Identifier(user)), (password,))
    else:
        cur.execute(
            sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD %s").format(sql.Identifier(user)),
            (password,),
        )


def apply_roles() -> dict:
    """Create RO users and lock CONNECT to their own database only."""
    applied: list[str] = []
    # One RO user per cluster admin DB, then CONNECT grants per source db.
    by_cluster: dict[str, list[str]] = {k: [] for k in CLUSTERS}
    for key, spec in SOURCES.items():
        by_cluster[spec["cluster"]].append(key)

    for cluster, keys in by_cluster.items():
        admin = connect_cluster_admin(cluster)
        admin.autocommit = True
        with admin.cursor() as cur:
            for key in keys:
                spec = SOURCES[key]
                _ensure_login(cur, spec["ro_user"], spec["ro_password"])
            # Revoke PUBLIC on every db this cluster owns, then grant per owner.
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
            owned = {spec["dbname"] for spec in (SOURCES[k] for k in keys)}
            for (datname,) in cur.fetchall():
                if datname in owned:
                    continue
                # leftover template/postgres: leave PUBLIC as the image set it
        admin.close()

        for key in keys:
            spec = SOURCES[key]
            admin = connect_cluster_admin(cluster)
            admin.autocommit = True
            with admin.cursor() as cur:
                _revoke_public_and_grant(cur, spec["dbname"], spec["ro_user"])
                # Other RO users on this cluster must not CONNECT here.
                for other in keys:
                    if other == key:
                        continue
                    cur.execute(
                        sql.SQL("REVOKE CONNECT ON DATABASE {} FROM {}").format(
                            sql.Identifier(spec["dbname"]),
                            sql.Identifier(SOURCES[other]["ro_user"]),
                        )
                    )
            admin.close()

            db = connect_source(key)
            db.autocommit = True
            schema = spec["schema"]
            ro = spec["ro_user"]
            with db.cursor() as cur:
                cur.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(schema), sql.Identifier(ro)))
                cur.execute(
                    sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA {} TO {}").format(
                        sql.Identifier(schema), sql.Identifier(ro)
                    )
                )
                cur.execute(
                    sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT SELECT ON TABLES TO {}").format(
                        sql.Identifier(schema), sql.Identifier(ro)
                    )
                )
            db.close()
            applied.append(f"{ro}@{spec['dbname']}")
    return {"ok": True, "roles": applied}
