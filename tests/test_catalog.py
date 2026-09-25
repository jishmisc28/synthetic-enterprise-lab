"""Catalog kinds and Aarohan instances — no Docker."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.catalog import AAROHAN_SOURCES, KIND_GUIDE, snapshot


class Catalog(unittest.TestCase):
    def test_kinds_cover_the_menu(self):
        for kind in ("postgres", "http-api", "erp", "saas", "events", "files", "object-store", "mail", "webhook"):
            self.assertIn(kind, KIND_GUIDE)

    def test_every_source_has_a_model_and_probe(self):
        ids = {s["id"] for s in AAROHAN_SOURCES}
        self.assertIn("s1-lms", ids)
        self.assertIn("s8-erp", ids)
        self.assertIn("s7-crm", ids)
        self.assertIn("minio", ids)
        for src in AAROHAN_SOURCES:
            self.assertTrue(src.get("model"), msg=src["id"])
            self.assertTrue(src.get("probe"), msg=src["id"])
            self.assertIn(src["kind"], KIND_GUIDE)

    def test_crm_is_saas_http_not_postgres(self):
        by_id = {s["id"]: s for s in AAROHAN_SOURCES}
        self.assertEqual(by_id["s7-crm"]["kind"], "saas")
        self.assertEqual(by_id["s7-crm"]["protocol"], "http")
        self.assertIn("/crm/", by_id["s7-crm"]["model"])
        self.assertEqual(by_id["s8-erp"]["kind"], "erp")

    def test_client_transports_are_honest(self):
        by_id = {s["id"]: s for s in AAROHAN_SOURCES}
        self.assertEqual(by_id["s1-lms"]["kind"], "postgres")
        self.assertEqual(by_id["s1-lms"]["port"], 55432)
        self.assertEqual(by_id["s4-coll"]["port"], 55433)
        self.assertEqual(by_id["s8-gl"]["port"], 55434)
        self.assertEqual(by_id["s5-gold"]["port"], 55435)
        self.assertEqual(by_id["s2-pay"]["kind"], "files")
        self.assertEqual(by_id["s3-bureau"]["kind"], "files")
        self.assertEqual(by_id["s6-vehicle"]["kind"], "files")
        self.assertEqual(by_id["s9-masters"]["kind"], "files")
        self.assertEqual(by_id["s2-events"]["direction"], "pull")
        self.assertIn("archive", by_id["s2-pay"])
        self.assertIn("not the client path", by_id["s2-pay"]["archive"]["note"])

    def test_snapshot_shape(self):
        snap = snapshot()
        self.assertEqual(snap["product"], "Synthetic Enterprise Lab")
        self.assertEqual(snap["domain"], "aarohan")
        self.assertIn("sources", snap)
        self.assertIn("kinds", snap)
        self.assertIn("down", snap)
        self.assertGreaterEqual(len(snap["sources"]), 14)
        for row in snap["sources"]:
            self.assertIn("health", row)
            self.assertIn("status", row["health"])


if __name__ == "__main__":
    unittest.main()
