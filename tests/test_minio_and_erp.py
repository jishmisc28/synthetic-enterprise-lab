"""Dated MinIO keys and ERP 401 — no Docker."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.minio_landing import LANDING_OBJECTS, keys_for


class DatedKeys(unittest.TestCase):
    def test_every_partner_shape_has_a_dated_prefix(self):
        for rel, keys in LANDING_OBJECTS.items():
            self.assertTrue(keys, msg=rel)
            self.assertTrue(any("/20" in k for k in keys), msg=rel)

    def test_payments_keeps_legacy_key(self):
        keys = keys_for("payments/upi_2026-08.csv.gz")
        self.assertIn("payments/2026-08-31/upi_2026-08.csv.gz", keys)
        self.assertIn("payments/upi_2026-08.csv.gz", keys)

    def test_bureau_collections_vehicle_masters(self):
        self.assertIn("bureau/2026-07-31/bureau_2026-07.jsonl", keys_for("bureau/bureau_2026-07.jsonl"))
        self.assertIn("collections/2026-08-31/ptp_register.xlsx", keys_for("collections/ptp_register.xlsx"))
        self.assertIn("vehicle/2026-08-31/commissions_partner.csv", keys_for("vehicle/commissions_partner.csv"))
        self.assertIn("masters/2026-08-31/identity_override.fwf", keys_for("masters/identity_override.fwf"))


class ErpAuth(unittest.TestCase):
    def test_missing_and_bad_bearer_are_401(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("fastapi not installed on host")
        from runtime.erp import app

        client = TestClient(app, raise_server_exceptions=False)
        self.assertEqual(client.get("/gl/journals").status_code, 401)
        self.assertEqual(client.get("/gl/journals", headers={"Authorization": "Bearer wrong"}).status_code, 401)
        self.assertEqual(client.get("/health").status_code, 200)


if __name__ == "__main__":
    unittest.main()
