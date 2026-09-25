#!/usr/bin/env python3
"""Print client connections. This script does not call any product."""

from __future__ import annotations

import json

CONNECTIONS = [
    {
        "id": "s1-lms",
        "transport": "postgres",
        "host": "127.0.0.1",
        "port": 55432,
        "database": "aarohan_lms",
        "schema": "lms",
        "username": "lms_ro",
        "password": "lms_ro_dev",
    },
    {
        "id": "s4-collections",
        "transport": "postgres",
        "host": "127.0.0.1",
        "port": 55433,
        "database": "aarohan_coll",
        "schema": "coll",
        "username": "coll_ro",
        "password": "coll_ro_dev",
    },
    {
        "id": "s5-gold",
        "transport": "postgres",
        "host": "127.0.0.1",
        "port": 55435,
        "database": "aarohan_gold",
        "schema": "gold",
        "username": "gold_ro",
        "password": "gold_ro_dev",
    },
    {
        "id": "s8-gl",
        "transport": "postgres",
        "host": "127.0.0.1",
        "port": 55434,
        "database": "aarohan_gl",
        "schema": "gl",
        "username": "gl_ro",
        "password": "gl_ro_dev",
    },
    {
        "id": "s2-payments-files",
        "transport": "s3",
        "endpoint": "http://127.0.0.1:19000",
        "bucket": "aarohan-landing",
        "prefix": "payments/",
        "access_key": "aarohan",
        "secret_key": "aarohan-minio-dev",
    },
    {
        "id": "s2-payments-events",
        "transport": "http",
        "url": "http://127.0.0.1:18081/payments",
        "authorization": "Bearer aarohan-dev",
        "direction": "pull",
    },
    {
        "id": "s7-crm",
        "transport": "http",
        "url": "http://127.0.0.1:18080/crm/accounts",
        "authorization": "Bearer aarohan-dev",
    },
    {
        "id": "s8-erp",
        "transport": "http",
        "url": "http://127.0.0.1:18080/gl/journals",
        "authorization": "Bearer aarohan-dev",
    },
]


def main() -> None:
    print(json.dumps(CONNECTIONS, indent=2))


if __name__ == "__main__":
    main()
