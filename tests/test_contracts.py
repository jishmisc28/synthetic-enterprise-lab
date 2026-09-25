"""Load defects must stay impossible. No Docker required."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AAROHAN = ROOT / "domains" / "aarohan"
sys.path.insert(0, str(ROOT / "domains"))
sys.path.insert(0, str(ROOT))


class LoadSqlDefects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.load = (AAROHAN / "sql" / "load.sql").read_text()
        cls.schema = (AAROHAN / "sql" / "00_lms_schema.sql").read_text()

    def test_no_invalid_psql_interpolation(self):
        self.assertNotIn(":'lms_dir'", self.load)
        self.assertNotIn(":lms_dir", self.load)
        self.assertIn("\\copy", self.load)

    def test_dimensions_load_first(self):
        prod = self.load.index("lms.product")
        branch = self.load.index("lms.branch")
        customer = self.load.index("lms.customer")
        loan = self.load.index("lms.loan_account")
        self.assertLess(prod, customer)
        self.assertLess(branch, customer)
        self.assertLess(customer, loan)

    def test_schema_has_csv_extra_columns(self):
        product = self.schema.split("CREATE TABLE lms.product")[1].split("\n);")[0]
        self.assertIn("min_p", product)
        self.assertIn("max_p", product)
        branch = self.schema.split("CREATE TABLE lms.branch")[1].split("\n);")[0]
        self.assertIn("effective_to", branch)
        self.assertIn("superseded_by", branch)

    def test_npa_flag_defaults_not_null(self):
        body = self.schema.split("CREATE TABLE lms.loan_account")[1].split("\n);")[0]
        self.assertRegex(body, r"npa_flag\s+boolean\s+NOT NULL")

    def test_rule_set_has_payload(self):
        body = self.schema.split("CREATE TABLE lms.rule_set")[1].split("\n);")[0]
        self.assertIn("payload", body)
        self.assertIn("jsonb", body)
        self.assertIn("lms.rule_set (rule_code, product_code, effective_from, effective_to, payload)", self.load)

    def test_copy_uses_column_lists(self):
        copies = [ln for ln in self.load.splitlines() if ln.startswith("\\copy")]
        self.assertGreaterEqual(len(copies), 10)
        for ln in copies:
            self.assertRegex(ln, r"\\copy \S+ \([^)]+\) FROM")


class GeneratorPks(unittest.TestCase):
    def test_tiny_typed_pks_unique(self):
        from aarohan.constants import SEED
        from aarohan.estate import build_estate

        e = build_estate("tiny", SEED)
        self.assertEqual(len({c["cif"] for c in e.customers}), len(e.customers))
        self.assertEqual(len({k["kyc_id"] for k in e.kyc}), len(e.kyc))
        self.assertEqual(len({ln["loan_no"] for ln in e.loans}), len(e.loans))
        agents = {(a["agent_code"], str(a["effective_from"])) for a in e.masters["agent_hierarchy"]}
        self.assertEqual(len(agents), len(e.masters["agent_hierarchy"]))
        for ln in e.loans:
            self.assertIn(ln.get("npa_flag"), (True, False))
        pans = [c["pan"] for c in e.customers]
        self.assertLess(len(set(pans)), len(pans), msg="CIF twins share a PAN; that is not a PK collision")


class LabBoundary(unittest.TestCase):
    def test_no_application_import(self):
        banned = ("from lib.", "from app.", "import lib.", "import app.")
        for folder in ("runtime", "scripts", "domains"):
            for path in (ROOT / folder).rglob("*.py"):
                text = path.read_text()
                for token in banned:
                    self.assertNotIn(token, text, msg=str(path.relative_to(ROOT)))

    def test_ports_documented(self):
        compose = (ROOT / "docker-compose.yml").read_text()
        self.assertIn("55432:5432", compose)
        self.assertIn("55433:5432", compose)
        self.assertIn("55434:5432", compose)
        self.assertIn("55435:5432", compose)
        self.assertIn("55436:5432", compose)
        self.assertIn("18080:18080", compose)
        self.assertIn("18081:18081", compose)
        self.assertIn("18082:18082", compose)
        self.assertIn("18083:18083", compose)
        self.assertIn("19000:9000", compose)
        self.assertIn("name: synthetic-enterprise-lab", compose)
        self.assertIn("postgres-lms", compose)
        self.assertIn("postgres-coll", compose)
        self.assertIn("postgres-gold", compose)
        self.assertIn("postgres-gl", compose)
        self.assertIn("postgres-archive", compose)

    def test_nine_databases(self):
        from runtime.pg import DATABASES, SOURCES

        for name in (
            "aarohan_lms", "aarohan_pay", "aarohan_bureau", "aarohan_coll",
            "aarohan_gold", "aarohan_veh", "aarohan_crm", "aarohan_gl",
            "aarohan_masters",
        ):
            self.assertIn(name, DATABASES.values())
        self.assertTrue(SOURCES["lms"]["client"])
        self.assertTrue(SOURCES["coll"]["client"])
        self.assertTrue(SOURCES["gold"]["client"])
        self.assertTrue(SOURCES["gl"]["client"])
        self.assertFalse(SOURCES["pay"]["client"])
        archive = (ROOT / "sql" / "00_create_archive_databases.sql").read_text()
        self.assertIn("aarohan_pay", archive)
        self.assertNotIn("aarohan_lms", archive)

    def test_health_page_exists(self):
        page = (ROOT / "static" / "index.html").read_text()
        self.assertIn("/catalog", page)
        self.assertIn("/healthz", page)
        self.assertIn("Synthetic Enterprise Lab", page)


if __name__ == "__main__":
    unittest.main()
