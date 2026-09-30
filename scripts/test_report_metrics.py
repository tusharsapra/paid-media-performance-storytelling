#!/usr/bin/env python3
"""Behavioural regression tests using fictional inputs."""
import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from report_metrics import DataError, analyse, change, serializable

ROOT = Path(__file__).resolve().parents[1]


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.config = json.loads((ROOT / "assets/sample-brief.json").read_text())
        with (ROOT / "assets/sample-performance.csv").open(newline="") as stream:
            self.rows = list(csv.DictReader(stream))
        self.columns = list(self.rows[0])

    def tearDown(self):
        self.temp.cleanup()

    def run_analysis(self, groups=()):
        path = self.directory / "input.csv"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, self.columns)
            writer.writeheader()
            writer.writerows(self.rows)
        return analyse(path, self.config, groups)

    def current(self, result):
        return next(g for g in result["groups"] if g["period_id"] == "current")

    def test_total_and_plan(self):
        result = self.run_analysis()
        group = self.current(result)
        self.assertEqual(group["totals"]["spend"], Decimal(80000))
        self.assertEqual(group["totals"]["primary_outcomes"], Decimal(600))
        self.assertEqual(group["metrics"]["target_attainment_pct"], Decimal(120))
        self.assertEqual(group["metrics"]["budget_utilisation_pct"], Decimal(80))
        self.assertAlmostEqual(float(group["metrics"]["cost_per_primary_outcome"]), 133.3333333)
        self.assertEqual(len(group["evidence"]), 2)

    def test_quality_and_growth(self):
        result = self.run_analysis()
        group = self.current(result)
        self.assertEqual(group["metrics"]["qualification_rate_pct"], Decimal(30))
        self.assertAlmostEqual(float(group["metrics"]["cost_per_qualified_outcome"]), 444.4444444)
        changes = result["comparisons"][0]["changes"]
        self.assertEqual(changes["qualified_outcomes"]["absolute"], Decimal(0))
        self.assertEqual(changes["qualification_rate_pct"]["percentage_points"], Decimal(-10))
        self.assertAlmostEqual(float(changes["primary_outcomes"]["relative_pct"]), 33.3333333)

    def test_weighted_rates_not_average(self):
        group = self.current(self.run_analysis())
        self.assertAlmostEqual(float(group["metrics"]["ctr_pct"]), 19000 / 1550000 * 100)
        self.assertNotAlmostEqual(float(group["metrics"]["ctr_pct"]), 1.5)

    def test_segment_targets_not_repeated(self):
        result = self.run_analysis(("market",))
        self.assertEqual(len(result["groups"]), 4)
        self.assertTrue(result["warnings"])
        for group in result["groups"]:
            self.assertNotIn("target_attainment_pct", group["metrics"])

    def test_no_target_no_attainment(self):
        self.config.pop("targets")
        self.assertNotIn("target_attainment_pct", self.current(self.run_analysis())["metrics"])

    def test_missing_outcome_withholds_total_and_ratio(self):
        self.rows[2]["primary_outcomes"] = ""
        group = self.current(self.run_analysis())
        self.assertIsNone(group["totals"]["primary_outcomes"])
        self.assertIsNone(group["metrics"]["cost_per_primary_outcome"])
        self.assertIsNone(group["metrics"]["target_attainment_pct"])
        self.assertEqual(group["coverage"]["primary_outcomes"]["present_rows"], 1)

    def test_zero_outcomes_is_not_zero_cost(self):
        for row in self.rows[2:]:
            row["primary_outcomes"] = row["qualified_outcomes"] = "0"
        group = self.current(self.run_analysis())
        self.assertIsNone(group["metrics"]["cost_per_primary_outcome"])
        self.assertTrue(any("No primary" in w for w in group["warnings"]))

    def test_zero_baseline_reports_absolute_only(self):
        self.assertEqual(change(Decimal(10), Decimal(0))["absolute"], 10)
        self.assertIsNone(change(Decimal(10), Decimal(0))["relative_pct"])

    def test_duplicate_grain_rejected_even_new_row_id(self):
        extra = copy.deepcopy(self.rows[0])
        extra["row_id"] = "new-id"
        self.rows.append(extra)
        with self.assertRaises(DataError):
            self.run_analysis()

    def test_unknown_basis_blocks_comparison_and_unit_cost(self):
        self.config["scopes"]["lead-generation"]["primary_outcome"]["source"] = "unknown"
        result = self.run_analysis()
        self.assertEqual(len(result["blocked_comparisons"]), 1)
        self.assertFalse(result["comparisons"])
        self.assertIsNone(self.current(result)["metrics"]["cost_per_primary_outcome"])

    def test_unconfirmed_click_population_blocks_rate(self):
        self.config["scopes"]["lead-generation"]["click_outcome_compatible"] = False
        self.assertIsNone(self.current(self.run_analysis())["metrics"]["click_to_outcome_rate_pct"])

    def test_lifecycle_snapshot_has_no_qualification_rate(self):
        self.config["scopes"]["lead-generation"]["qualified_outcome"]["same_cohort"] = False
        self.assertIsNone(self.current(self.run_analysis())["metrics"]["qualification_rate_pct"])

    def test_qualified_cannot_exceed_same_cohort_raw(self):
        self.rows[2]["qualified_outcomes"] = "401"
        with self.assertRaises(DataError):
            self.run_analysis()

    def test_unequal_period_blocks_without_confirmation(self):
        self.config["periods"]["current"]["end"] = "2025-06-20"
        self.config["comparisons"][0].pop("periods_comparable")
        result = self.run_analysis()
        self.assertIn("unequal", result["blocked_comparisons"][0]["reasons"][0])

    def test_overlapping_periods_block(self):
        self.config["periods"]["current"].update(start="2025-04-15", end="2025-05-14")
        self.assertTrue(self.run_analysis()["blocked_comparisons"])

    def test_provisional_warning(self):
        self.config["periods"]["current"]["status"] = "provisional"
        result = self.run_analysis()
        self.assertTrue(any("provisional" in w for w in self.current(result)["warnings"]))
        self.assertTrue(result["comparisons"][0]["warnings"])

    def test_absent_segment_not_assumed_zero(self):
        self.rows = [r for r in self.rows if r["row_id"] != "r4"]
        result = self.run_analysis(("market",))
        self.assertEqual(len(result["comparisons"]), 1)
        self.assertTrue(any("absent" in r for b in result["blocked_comparisons"] for r in b["reasons"]))

    def test_currency_scopes_never_pooled(self):
        other = copy.deepcopy(self.config["scopes"]["lead-generation"])
        other["currency"] = "EUR"
        self.config["scopes"]["euro-scope"] = other
        extra = copy.deepcopy(self.rows[2])
        extra.update(row_id="r5", scope_id="euro-scope")
        self.rows.append(extra)
        result = self.run_analysis()
        self.assertEqual(len(result["groups"]), 3)
        self.assertEqual(self.current(result)["totals"]["spend"], Decimal(45000))
        usd = next(g for g in result["groups"] if g["scope_id"] == "lead-generation" and g["period_id"] == "current")
        self.assertEqual(usd["totals"]["spend"], Decimal(80000))

    def test_fractional_attribution_preserved(self):
        self.rows[2]["primary_outcomes"] = "400.25"
        self.assertEqual(self.current(self.run_analysis())["totals"]["primary_outcomes"], Decimal("600.25"))

    def test_negative_adjustments_require_declaration(self):
        self.rows[2]["spend"] = "-100"
        with self.assertRaises(DataError):
            self.run_analysis()
        self.config["scopes"]["lead-generation"]["allow_adjustments"] = True
        group = self.current(self.run_analysis())
        self.assertEqual(group["totals"]["spend"], 34900)
        self.assertTrue(any("negative" in w for w in group["warnings"]))

    def test_nonfinite_value_rejected(self):
        self.rows[2]["spend"] = "NaN"
        with self.assertRaises(DataError):
            self.run_analysis()

    def test_proxy_values_not_roas(self):
        self.config["scopes"]["lead-generation"]["revenue"] = {
            "kind": "proxy", "definition": "fictional quality points", "source": "fictional scoring",
            "spend_compatible": True}
        for row in self.rows:
            row["revenue"] = "1000"
        group = self.current(self.run_analysis())
        self.assertIsNone(group["metrics"]["roas"])
        self.assertEqual(group["metrics"]["proxy_value_to_cost"], Decimal("0.025"))

    def test_monetary_revenue_currency_alignment(self):
        scope = self.config["scopes"]["lead-generation"]
        scope["revenue"] = {"kind": "monetary", "definition": "net paid revenue", "source": "fictional orders",
                            "currency": "EUR", "spend_compatible": True}
        for row in self.rows:
            row["revenue"] = "80000"
        self.assertIsNone(self.current(self.run_analysis())["metrics"]["roas"])
        scope["revenue"]["currency"] = "USD"
        self.assertEqual(self.current(self.run_analysis())["metrics"]["roas"], Decimal(2))

    def test_target_basis_and_duplicates_rejected(self):
        self.config["targets"][0]["basis_confirmed"] = False
        with self.assertRaises(DataError):
            self.run_analysis()
        self.config["targets"][0]["basis_confirmed"] = True
        self.config["targets"].append(copy.deepcopy(self.config["targets"][0]))
        with self.assertRaises(DataError):
            self.run_analysis()

    def test_cli_and_input_preservation(self):
        data = ROOT / "assets/sample-performance.csv"
        brief = ROOT / "assets/sample-brief.json"
        before = data.read_bytes()
        output = self.directory / "output.json"
        command = [sys.executable, str(ROOT / "scripts/report_metrics.py"), "--data", str(data), "--config", str(brief)]
        process = subprocess.run(command + ["--output", str(output)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(output.read_text())["schema_version"], 1)
        self.assertEqual(data.read_bytes(), before)
        process = subprocess.run(command + ["--output", str(data)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(data.read_bytes(), before)

    def test_json_serialization_no_nan(self):
        json.dumps(serializable(self.run_analysis()), allow_nan=False)

    def test_malformed_config_rejected_cleanly(self):
        self.config = []
        with self.assertRaises(DataError):
            self.run_analysis()

    def test_targets_must_be_array(self):
        self.config["targets"] = {}
        with self.assertRaises(DataError):
            self.run_analysis()


if __name__ == "__main__":
    unittest.main(verbosity=2)
