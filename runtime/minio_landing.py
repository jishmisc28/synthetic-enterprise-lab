"""Upload partner landing files to MinIO. Adds dated keys; never deletes."""

from __future__ import annotations

import os
from pathlib import Path

from runtime.constants import ARCHIVE_BUCKET, LANDING_BUCKET

# local path under output/landing → dated object key, plus any legacy aliases to keep.
# Dates are the file's own period (close month or the month in the filename).
LANDING_OBJECTS: dict[str, tuple[str, ...]] = {
    "payments/upi_2026-08.csv.gz": (
        "payments/2026-08-31/upi_2026-08.csv.gz",
        "payments/upi_2026-08.csv.gz",  # wave-0 key already on the bucket; keep it
    ),
    "collections/ptp_register.xlsx": ("collections/2026-08-31/ptp_register.xlsx",),
    "bureau/bureau_2026-07.jsonl": ("bureau/2026-07-31/bureau_2026-07.jsonl",),
    "vehicle/commissions_partner.csv": ("vehicle/2026-08-31/commissions_partner.csv",),
    "masters/identity_override.fwf": ("masters/2026-08-31/identity_override.fwf",),
}

LANDING = Path(os.environ.get("LAB_LANDING", "/data/landing"))


def keys_for(rel: str) -> tuple[str, ...]:
    rel = rel.replace("\\", "/").lstrip("/")
    return LANDING_OBJECTS.get(rel, (rel,))


def upload_path(client, local: Path, landing_root: Path | None = None) -> list[str]:
    root = landing_root or LANDING
    rel = str(local.relative_to(root)).replace("\\", "/")
    put = []
    for key in keys_for(rel):
        client.fput_object(LANDING_BUCKET, key, str(local))
        put.append(key)
    return put


def ensure_buckets(client) -> None:
    for bucket in (LANDING_BUCKET, ARCHIVE_BUCKET):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)


def make_client():
    from minio import Minio

    endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    endpoint = endpoint.replace("http://", "").replace("https://", "")
    return Minio(
        endpoint,
        access_key=os.environ.get("MINIO_ROOT_USER", "aarohan"),
        secret_key=os.environ.get("MINIO_ROOT_PASSWORD", "aarohan-minio-dev"),
        secure=False,
    )


def upload_landing(landing_root: Path | None = None) -> dict:
    """Add every file under the landing folder. Does not remove existing objects."""
    root = landing_root or LANDING
    client = make_client()
    ensure_buckets(client)
    uploaded: list[str] = []
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file():
                uploaded.extend(upload_path(client, path, root))
    return {"status": "ok", "uploaded": uploaded, "count": len(uploaded)}


def upload_one(local: Path, landing_root: Path | None = None) -> list[str]:
    if os.environ.get("MINIO_OPTIONAL", "0") == "1":
        return []
    try:
        client = make_client()
        ensure_buckets(client)
        return upload_path(client, local, landing_root)
    except Exception:
        return []
