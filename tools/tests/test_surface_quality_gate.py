"""Offline synthetic gate regressions; no real print or physical evidence exists here."""
from copy import deepcopy
import unittest

import test_engineering_harness as fixture

eh = fixture.eh


class SurfaceQualityGateTests(unittest.TestCase):
    def setUp(self):
        fixture.EngineeringHarnessTests.setUp(self)

    def part(self):
        return self.run["manufacturing_quality"]["parts"]["bracket"]

    def surface(self):
        return self.part()["surfaces"][0]

    def plate(self):
        return self.run["manufacturing_quality"]["plates"]["plate01"]

    def mark(self, check_id, status="PASS", evidence=None):
        self.h.mark(self.run, check_id, "plate:plate01" if check_id == "native-support-stability" else "part:bracket",
                    status, "TEST ONLY fictional complete quality observations, no real print claim",
                    self.run["owner"], "inspection", list(self.run["artifacts"]) if evidence is None else evidence,
                    "TEST ONLY complete per-face/per-edge/per-support table and exact layers")

    def complete(self):
        fixture.EngineeringHarnessTests.complete(self)

    def ref(self, key="proof"):
        return {"artifact": key, "sha256": self.run["artifacts"][key]["sha256"],
                "locator": "TEST ONLY synthetic feature/coupon bounds and layers"}

    def coupon(self):
        self.run["purpose"] = "calibration"
        self.surface()["strategy"] = "bounded-surface-calibration"
        self.surface().pop("physical_validation", None)
        self.run["manufacturing_quality"]["calibration_scope"] = {
            "kind": "surface-coupon", "full_product_part": False, "part_ids": ["bracket"],
            "hypothesis": "TEST ONLY fictional bounded supported underside experiment",
            "limits": "TEST ONLY coupon is not a complete product or fit prototype",
            "acceptance": "TEST ONLY fictional finish and edge curl measurements",
            "evidence": self.ref(), "geometry_evidence": self.ref("mesh")}

    def test_every_new_check_required_at_exact_scope_and_cannot_be_missing(self):
        catalog = {c["id"]: c for c in self.h.catalog}
        self.assertTrue(eh.QUALITY_CHECKS <= set(catalog))
        self.complete()
        original = deepcopy(self.run)
        for check_id in eh.QUALITY_CHECKS:
            with self.subTest(check=check_id):
                self.run = deepcopy(original)
                self.run["checks"] = [r for r in self.run["checks"] if r["id"] != check_id]
                result = self.h.validate(self.run, "release")
                self.assertFalse(result["passed"])
                self.assertTrue(any(check_id in e and "missing check" in e for e in result["errors"]))

    def test_new_quality_checks_cannot_be_another_freeform_pass(self):
        self.run.pop("manufacturing_quality")
        for check_id in eh.QUALITY_CHECKS:
            with self.subTest(check=check_id), self.assertRaisesRegex(eh.HarnessError, "manufacturing_quality"):
                self.mark(check_id)

    def test_manually_stamped_all_pass_rows_still_cannot_waive_unknown_surface(self):
        self.complete()
        self.surface().pop("physical_validation")
        for c, target in self.h.required(self.run, "release"):
            row = next(r for r in self.run["checks"] if r["id"] == c["id"] and r["target"] == target)
            row["basis_sha256"] = self.h.basis(self.run, c["stage"])
        result = self.h.validate(self.run, "release")
        self.assertFalse(result["passed"])
        self.assertTrue(any("actual accepted physical test required" in e for e in result["errors"]))

    def test_production_label_does_not_waive_supported_quality(self):
        for purpose in ("production",):
            with self.subTest(purpose=purpose):
                self.run["purpose"] = purpose
                self.surface()["strategy"] = "bounded-surface-calibration"
                with self.assertRaisesRegex(eh.HarnessError, "bounded surface-coupon"):
                    self.mark("surface-quality-strategy")

    def test_only_explicit_bounded_surface_coupon_can_investigate_unknown_quality(self):
        self.coupon()
        self.complete()
        result = self.h.validate(self.run, "release")
        self.assertTrue(result["passed"], result["errors"])
        self.run["manufacturing_quality"]["calibration_scope"]["full_product_part"] = True
        with self.assertRaisesRegex(eh.HarnessError, "full product parts"):
            self.mark("supported-surface-quality")

    def test_coupon_scope_needs_every_part_geometry_bounds_and_acceptance(self):
        self.coupon()
        original = deepcopy(self.run)
        for field, value in (("part_ids", []), ("part_ids", [["bracket"]]), ("limits", ""),
                             ("acceptance", ""), ("geometry_evidence", None), ("evidence", None)):
            with self.subTest(field=field, value=value):
                self.run = deepcopy(original)
                self.run["manufacturing_quality"]["calibration_scope"][field] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark("surface-quality-strategy")

    def test_missing_acceptance_area_or_supported_strategy_is_rejected(self):
        original = deepcopy(self.run)
        for field, value in (("acceptance", "looks good"), ("area_mm2", 0), ("area_mm2", float("inf")),
                             ("max_span_mm", -1), ("strategy", "direct-print"), ("class", "unknown")):
            with self.subTest(field=field):
                self.run = deepcopy(original)
                self.surface()[field] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark("surface-quality-strategy")

    def test_profile_name_virtual_preview_or_unknown_test_is_not_physical_validation(self):
        original = deepcopy(self.run)
        for field, value in (("source", "slicer-preview"), ("result", "unknown"), ("result", "failed"),
                             ("process_signature", "ELEGOO PETG GOOD PROFILE"), ("equivalence", ""),
                             ("geometry_evidence", None), ("project_equivalence_evidence", None),
                             ("test_actor", ""), ("sample_id", ""), ("observed_at", ""), ("material_condition", "")):
            with self.subTest(field=field):
                self.run = deepcopy(original)
                self.surface()["physical_validation"][field] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark("supported-surface-quality")

    def test_physical_match_requires_every_exact_material_and_resolved_profile(self):
        original = deepcopy(self.run)
        for key in ("machine", "filament", "process"):
            with self.subTest(profile=key):
                self.run = deepcopy(original)
                path = self.root / self.run["artifacts"][key]["path"]
                previous = path.read_text()
                path.write_text(previous + "TEST ONLY changed setting\n")
                self.h.bind(self.run, key, str(path), self.run["artifacts"][key]["role"])
                with self.assertRaisesRegex(eh.HarnessError, "all current resolved settings"):
                    self.mark("supported-surface-quality")
                path.write_text(previous)
        self.run = deepcopy(original)
        self.run["profile"]["material"]["variant"] = "other-petg"
        self.run["profile"]["material"]["manufacturer"] = "TEST OTHER MAKER"
        self.run["profile"]["material"]["product"] = "TEST OTHER PETG"
        with self.assertRaisesRegex(eh.HarnessError, "exact material"):
            self.mark("supported-surface-quality")

    def test_all_five_physical_criteria_are_required(self):
        original = deepcopy(self.run)
        for criterion in ("surface-finish", "dimensional-integrity", "layer-bonding", "edge-curl", "removability"):
            with self.subTest(criterion=criterion):
                self.run = deepcopy(original)
                self.surface()["physical_validation"]["criteria"].pop(criterion)
                with self.assertRaisesRegex(eh.HarnessError, criterion):
                    self.mark("supported-surface-quality")

    def test_slice_must_describe_actual_interface_first_model_layer_and_anchoring(self):
        for field in ("first_model_z_mm", "unsupported_span_mm", "interface_gap_mm", "interface_pitch_mm",
                      "anchoring", "line_direction", "edge_formation", "evidence"):
            original = self.surface()["slice"].pop(field)
            with self.subTest(field=field), self.assertRaises(eh.HarnessError):
                self.mark("supported-surface-quality")
            self.surface()["slice"][field] = original

    def test_model_curl_cannot_be_substituted_by_support_root_stability(self):
        self.plate()["support_groups"][0].pop("model_edge_curl")
        with self.assertRaisesRegex(eh.HarnessError, "model_edge_curl"):
            self.mark("native-support-stability")

    def test_bridge_physical_strategy_cannot_use_na_or_skip_physical_proof(self):
        self.surface()["formation"] = "bridge"
        self.mark("supported-surface-quality")
        with self.assertRaisesRegex(eh.HarnessError, "N/A forbidden"):
            self.mark("supported-surface-quality", "N/A")
        self.surface().pop("physical_validation")
        with self.assertRaisesRegex(eh.HarnessError, "actual accepted physical test required"):
            self.mark("supported-surface-quality")

    def test_each_support_group_needs_root_interface_curl_collision_and_removal(self):
        for field in ("root_stability", "interface_coverage", "model_edge_curl", "nozzle_collision", "removal_access"):
            value = self.plate()["support_groups"][0][field]
            self.plate()["support_groups"][0][field] = {**value, "result": "unknown"}
            with self.subTest(field=field), self.assertRaisesRegex(eh.HarnessError, field):
                self.mark("native-support-stability")
            self.plate()["support_groups"][0][field] = value

    def test_cannot_omit_support_group_or_uncovered_supported_face(self):
        self.plate()["support_groups"] = []
        with self.assertRaisesRegex(eh.HarnessError, "every supported model face"):
            self.mark("native-support-stability")

    def test_no_supports_na_requires_empty_groups_and_no_supported_faces(self):
        self.plate()["has_supports"] = False
        self.plate()["support_groups"] = []
        with self.assertRaisesRegex(eh.HarnessError, "every supported model face"):
            self.mark("native-support-stability", "N/A")
        self.surface()["formation"] = "build-plate"
        self.surface()["strategy"] = "direct-print"
        self.mark("native-support-stability", "N/A")
        self.mark("supported-surface-quality", "N/A")
        with self.assertRaisesRegex(eh.HarnessError, "N/A forbidden"):
            self.mark("free-edge-continuity", "N/A")

    def test_unjustified_thin_section_fallback_cannot_be_profile_wall_count(self):
        for field, value, message in (("min_roads", 2, "3 actual contiguous roads"),
                                      ("min_layers", 3, "4 actual continuous layers"),
                                      ("forming_base", "air", "real forming base"),
                                      ("continuous", False, "continuous"), ("seam_safe", False, "seam_safe"),
                                      ("base_supported", False, "base_supported")):
            previous = self.part()["edges"][0][field]
            self.part()["edges"][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(eh.HarnessError, message):
                self.mark("free-edge-continuity")
            self.part()["edges"][0][field] = previous
        # This rule changes no global wall-count/profile setting.
        self.assertNotIn("wall_loops", self.run["profile"])

    def test_edge_inventory_can_only_be_empty_with_explicit_evidenced_absence(self):
        self.part()["edges"] = []
        with self.assertRaisesRegex(eh.HarnessError, "no-free-or-functional-edges"):
            self.mark("free-edge-continuity")
        self.part()["no_edges_reason"] = "TEST ONLY fictional geometry has no free or functional edge features"
        self.mark("free-edge-continuity")

    def test_structured_evidence_hash_locator_and_row_citation_are_mandatory(self):
        self.surface()["physical_validation"]["geometry_evidence"]["sha256"] = "stale"
        with self.assertRaisesRegex(eh.HarnessError, "current evidence hash"):
            self.mark("supported-surface-quality")
        self.surface()["physical_validation"]["geometry_evidence"] = self.ref("mesh")
        with self.assertRaisesRegex(eh.HarnessError, "must cite every structured"):
            self.mark("supported-surface-quality", evidence=["proof"])
        self.surface()["evidence"]["locator"] = ""
        with self.assertRaisesRegex(eh.HarnessError, "locator"):
            self.mark("surface-quality-strategy")

    def test_quality_inventory_change_stales_preceding_design_review(self):
        self.complete()
        self.surface()["area_mm2"] += 1
        result = self.h.validate(self.run, "design")
        self.assertFalse(result["passed"])
        self.assertTrue(any("stale review basis" in e for e in result["errors"]))

    def test_supported_surface_procedure_is_hashed_policy_not_untracked_evidence(self):
        name = "harness/SUPPORTED-SURFACES-RU.md"
        self.assertIn(name, eh.POLICY_FILES)
        self.complete()
        old_basis = {stage: self.h.basis(self.run, stage) for stage in eh.STAGES}
        path = self.root / name
        path.write_text(path.read_text() + "\nTEST ONLY: changed mandatory surface acceptance procedure\n")
        for stage in eh.STAGES:
            with self.subTest(stage=stage):
                self.assertNotEqual(old_basis[stage], self.h.basis(self.run, stage))
                result = self.h.validate(self.run, stage)
                self.assertFalse(result["passed"])
                self.assertTrue(any("stale review basis" in e for e in result["errors"]))

    def test_malformed_quality_maps_fail_closed_instead_of_crashing(self):
        original = deepcopy(self.run)
        for value in ([], ["truthy-malformed-quality"], "unknown", True,
                      {"schema_version": 1}, {"schema_version": 1, "parts": [], "plates": {}}):
            with self.subTest(value=value):
                self.run = deepcopy(original)
                self.run["manufacturing_quality"] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark("surface-quality-strategy")
                for stage in eh.STAGES:
                    # Public basis is safe even when the caller has not yet run
                    # structural validation. mark/check still reject bad data.
                    self.assertEqual(len(self.h.basis(self.run, stage)), 64)
                    self.assertFalse(self.h.validate(self.run, stage)["passed"])

    def test_create_initializes_explicit_unknown_quality_without_auto_pass(self):
        fresh = self.h.create("new-quality-test", ["one", "two"], ["plate"], "other-petg", "production")
        quality = fresh["manufacturing_quality"]
        self.assertEqual(quality["schema_version"], 1)
        self.assertIsNone(quality["calibration_scope"])
        self.assertEqual(set(quality["parts"]), {"one", "two"})
        self.assertEqual(set(quality["plates"]), {"plate"})
        for part in quality["parts"].values():
            self.assertIsNone(part["inventory_evidence"])
            self.assertEqual(part["surfaces"], [])
            self.assertEqual(part["edges"], [])
        self.assertIsNone(quality["plates"]["plate"]["has_supports"])
        self.assertTrue(all(row["status"] == "UNKNOWN" for row in fresh["checks"]))
        for stage in eh.STAGES:
            self.assertFalse(self.h.validate(fresh, stage)["passed"])

    def test_malformed_nested_quality_entries_reject_through_full_public_api(self):
        self.complete()
        original = deepcopy(self.run)
        poisons = (("part", None), ("surfaces", {"wrong": "shape"}), ("surfaces", [None, ["bad"]]),
                   ("edges", [None]), ("part_id", []), ("part_id", {"bad": "id"}),
                   ("surface_ids", [["supported-lip"]]), ("physical_validation", "not-a-record"))
        for kind, value in poisons:
            with self.subTest(kind=kind, value=value):
                self.run = deepcopy(original)
                if kind == "part":
                    self.run["manufacturing_quality"]["parts"]["bracket"] = value
                elif kind in ("surfaces", "edges"):
                    self.part()[kind] = value
                elif kind in ("part_id", "surface_ids"):
                    self.plate()["support_groups"][0][kind] = value
                else:
                    self.surface()[kind] = value
                result = self.h.validate(self.run, "release")
                self.assertFalse(result["passed"])
                check_id = "native-support-stability" if kind in ("part_id", "surface_ids") else (
                    "supported-surface-quality" if kind == "physical_validation" else (
                    "free-edge-continuity" if kind == "edges" else "surface-quality-strategy"))
                with self.assertRaises(eh.HarnessError):
                    self.mark(check_id)


if __name__ == "__main__":
    unittest.main()
