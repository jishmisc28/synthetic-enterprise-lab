"""Tiny-scale invariants for Aarohan. Predicates, not manifesto copying."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG = ROOT.parent
sys.path.insert(0, str(PG))

from aarohan.constants import SEED, money
from aarohan.emit import emit
from aarohan.estate import build_estate
from aarohan.evaluate import evaluate
from aarohan.money import allocate, emi
from aarohan.rules import gold_ltv_limit, waterfall_order
from datetime import date


class MoneyAndRules(unittest.TestCase):
    def test_emi_scale_four(self):
        e = emi(Decimal("120000"), Decimal("0.1800"), 24)
        self.assertEqual(e.as_tuple().exponent, -4)

    def test_waterfall_flips_in_april_2025(self):
        self.assertEqual(waterfall_order("PL", date(2025, 3, 31))[0], "CHARGE")
        self.assertEqual(waterfall_order("PL", date(2025, 4, 1))[0], "INTEREST")
        self.assertEqual(waterfall_order("TW", date(2025, 5, 1))[0], "CHARGE")

    def test_gold_ltv_tightens(self):
        self.assertEqual(gold_ltv_limit(date(2025, 6, 30)), Decimal("0.85"))
        self.assertEqual(gold_ltv_limit(date(2025, 7, 1)), Decimal("0.75"))

    def test_allocate_leaves_unapplied(self):
        out = allocate(money(100), money(40), money(40), money(40), ("INTEREST", "CHARGE", "PRINCIPAL"))
        self.assertEqual(out["UNAPPLIED"], money(0))
        self.assertEqual(out["INTEREST"], money(40))


class TinyEstate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="aarohan-"))
        cls.estate = build_estate("tiny", SEED)
        emit(cls.estate, cls.tmpdir)
        cls.v = evaluate(cls.estate)
        cls.schema = (ROOT / "sql" / "00_lms_schema.sql").read_text()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_a2_fifteen_valid_and_eight_near_miss_i_series(self):
        valid = {g["incident_id"] for g in self.estate.ground_truth if g["kind"] == "valid"}
        near = {g["incident_id"] for g in self.estate.ground_truth if g["kind"] == "near_miss"}
        for i in range(1, 16):
            self.assertIn(f"I{i:02d}", valid)
        for nid in ("I01n", "I02n", "I03n", "I05n", "I07n", "I08n", "I10n", "I14n"):
            self.assertIn(nid, near)
        self.assertGreaterEqual(len(near) / (len(valid) + len(near)), 0.30)

    def test_a4_near_miss_absent_from_observed(self):
        near = {g["incident_id"] for g in self.estate.ground_truth
                if g["kind"] == "near_miss" and g.get("expected_detection") is False}
        observed = set()
        for m in self.v["monitors"].values():
            observed.update(m["observed"])
        # near-miss IDs themselves are not monitor keys; check their source records
        self.assertNotIn("AF-LN-I01N-PL", self.v["monitors"]["M1"]["observed"])
        self.assertNotIn("RCPT-I02N", self.v["monitors"]["M3"]["observed"])
        self.assertNotIn("CHG-I03N", self.v["monitors"]["M2"]["observed"])
        self.assertNotIn("INC-I05N", self.v["monitors"]["M5"]["observed"])
        self.assertNotIn("AF-AP-I08N", self.v["monitors"]["M6"]["observed"])
        self.assertNotIn("PKT-I10N", self.v["monitors"]["M7"]["observed"])
        self.assertNotIn("WO-I14N", self.v["monitors"]["M8"]["observed"])
        self.assertNotIn("CMP-GOLD-OK", self.v["monitors"]["M9"]["observed"])
        self.assertTrue(near)

    def test_named_monitor_keys(self):
        m = self.v["monitors"]
        self.assertIn("AF-LN-I01-PL", m["M1"]["observed"])
        self.assertIn("CHG-I03", m["M2"]["observed"])
        self.assertIn("INS-I04", m["M2"]["observed"])
        self.assertIn("RCPT-I02", m["M3"]["observed"])
        self.assertIn("AF-LN-M4-EMPTY", m["M4"]["observed"])
        self.assertIn("INC-I05", m["M5"]["observed"])
        self.assertIn("INC-I06", m["M5"]["observed"])
        self.assertIn("AF-AP-I08", m["M6"]["observed"])
        self.assertIn("AF-AP-I09", m["M6"]["observed"])
        self.assertIn("PKT-I10", m["M7"]["observed"])
        self.assertIn("PKT-I11", m["M7"]["observed"])
        self.assertIn("PKT-I12", m["M7"]["observed"])
        self.assertIn("WO-I14", m["M8"]["observed"])
        self.assertIn("REC-I15", m["M8"]["observed"])
        self.assertIn("CMP-I09", m["M9"]["observed"])
        self.assertIn("AF-LN-I01-PL", m["M10"]["observed"])
        self.assertIn("AF-LN-I13-GL", m["M10"]["observed"])
        self.assertIn("AF-LN-I07-TW", m["M10"]["observed"])

    def test_a8_m4_zero_absent(self):
        self.assertNotIn("AF-LN-M4-ZERO", self.v["monitors"]["M4"]["observed"])

    def test_a5_money_scale(self):
        for row in self.estate.loans:
            self.assertEqual(row["principal"].as_tuple().exponent, -4)
        for row in self.estate.charges:
            self.assertEqual(row["amount"].as_tuple().exponent, -4)
        for row in self.estate.s2:
            self.assertEqual(row["amount"].as_tuple().exponent, -4)

    def test_a6_no_payment_gateway_in_lms(self):
        self.assertNotIn("CREATE TABLE lms.payment_gateway_raw", self.schema)
        body = self.schema.split("CREATE TABLE lms.gold_pledge")[1].split(";")[0]
        self.assertNotIn("custody_state", body)

    def test_a7_gold_pledge_csv_has_no_custody(self):
        header = (self.tmpdir / "lms" / "gold_pledge.csv").read_text().splitlines()[0]
        self.assertNotIn("custody_state", header)
        self.assertTrue((self.tmpdir / "files" / "gold" / "packets.csv").exists())
        gold_h = (self.tmpdir / "files" / "gold" / "packets.csv").read_text().splitlines()[0]
        self.assertIn("custody_state", gold_h)

    def test_a9_k13_excludes_timing(self):
        self.assertNotIn("timing_not_break", self.v["monitors"]["M10"]["observed"])
        k13 = int(float(self.v["kpis"]["K13"]["value"]))
        self.assertEqual(k13, self.v["monitors"]["M10"]["count"])

    def test_owners_are_named_roles(self):
        emails = {g["owner_email"] for g in self.estate.ground_truth}
        self.assertTrue(emails)
        for em in emails:
            self.assertNotIn("operations@", em.lower())
            self.assertIn("@aarohan.example", em)

    def test_output_layout(self):
        self.assertTrue((self.tmpdir / "lms" / "loan_account.csv").exists())
        self.assertTrue((self.tmpdir / "files" / "payments" / "upi.csv").exists())
        self.assertTrue((self.tmpdir / "files" / "masters" / "rule_set.json").exists())
        self.assertTrue((self.tmpdir / "api" / "campaigns.json").exists())
        self.assertTrue((self.tmpdir / "ground_truth.json").exists())

    def test_a1_reproducible_ground_truth(self):
        a = build_estate("tiny", SEED)
        b = build_estate("tiny", SEED)
        from aarohan.emit import jsonable
        ja = json.dumps(jsonable(a.ground_truth), sort_keys=True)
        jb = json.dumps(jsonable(b.ground_truth), sort_keys=True)
        self.assertEqual(hashlib.sha256(ja.encode()).hexdigest(),
                         hashlib.sha256(jb.encode()).hexdigest())

    def test_typed_pks_are_unique_and_npa_flag_populated(self):
        cifs = [c["cif"] for c in self.estate.customers]
        self.assertEqual(len(cifs), len(set(cifs)))
        kycs = [k["kyc_id"] for k in self.estate.kyc]
        self.assertEqual(len(kycs), len(set(kycs)))
        dealers = [d["dealer_code"] for d in self.estate.masters["dealer_map"]]
        self.assertEqual(len(dealers), len(set(dealers)))
        for ln in self.estate.loans:
            self.assertIn(ln.get("npa_flag"), (True, False))
        header = (self.tmpdir / "lms" / "rule_set.csv").read_text().splitlines()[0]
        self.assertIn("payload", header)
        self.assertGreater(len(list(self.estate.rule_set)), 0)

    def test_schema_columns_cover_csv_headers(self):
        schema = self.schema
        pairs = {
            "lms.branch": "branch.csv",
            "lms.product": "product.csv",
            "lms.loan_account": "loan_account.csv",
            "lms.rule_set": "rule_set.csv",
        }
        for table, csv_name in pairs.items():
            hdr = (self.tmpdir / "lms" / csv_name).read_text().splitlines()[0].split(",")
            chunk = schema.split(f"CREATE TABLE {table}")[1]
            # Do not split on ';' inside SQL comments.
            body = chunk.split("\n);")[0]
            for col in hdr:
                self.assertIn(col, body, msg=f"{csv_name} column {col} missing from {table}")

    def test_matches_checked_in_expected(self):
        expected_path = ROOT / "expected" / "tiny" / "verification.json"
        if not expected_path.exists():
            self.skipTest("expected/tiny not checked in yet")
        expected = json.loads(expected_path.read_text())
        self.assertEqual(self.v["monitors"]["M1"]["observed"], expected["monitors"]["M1"]["observed"])
        self.assertEqual(self.v["monitors"]["M5"]["observed"], expected["monitors"]["M5"]["observed"])
        self.assertEqual(self.v["kpis"]["K12"]["value"], expected["kpis"]["K12"]["value"])


if __name__ == "__main__":
    unittest.main()
