"""Synthetic review-record regressions, never actual manufacturing evidence."""
from copy import deepcopy
import unittest

import test_engineering_harness as fixture

eh = fixture.eh


class EngineeringQualityBasisTests(unittest.TestCase):
    def setUp(self):
        fixture.EngineeringHarnessTests.setUp(self)

    def surface(self):
        return self.run["manufacturing_quality"]["parts"]["bracket"]["surfaces"][0]

    def edge(self):
        return self.run["manufacturing_quality"]["parts"]["bracket"]["edges"][0]

    def ref(self, key="proof"):
        return {"artifact": key, "sha256": self.run["artifacts"][key]["sha256"],
                "locator": "TEST ONLY exact synthetic feature, requirement and forming layers"}

    def observed(self):
        return {"result": "accepted",
                "observation": "TEST ONLY fictional purpose-specific comparison with measured geometry and process basis",
                "evidence": self.ref()}

    def engineering_surface(self):
        self.surface()["strategy"] = "engineering-justified"
        self.surface().pop("physical_validation", None)
        self.surface()["engineering_justification"] = {
            key: self.observed() for key in ("requirement_basis", "geometry_process_basis",
                                             "acceptance_budget", "toolpath_assessment")}

    def justified_section(self):
        self.edge().update({"min_roads": 2, "min_layers": 3,
                            "section_justification": {key: self.observed() for key in
                                                      ("requirement_basis", "actual_section_formation")}})

    def mark(self, check_id, evidence=None):
        self.h.mark(self.run, check_id, "part:bracket", "PASS",
                    "TEST ONLY actual synthetic basis, no real fit, quality or strength claim",
                    self.run["owner"], "inspection",
                    list(self.run["artifacts"]) if evidence is None else evidence,
                    "TEST ONLY full synthetic surface or edge and all actual forming layers")

    def test_engineering_supported_feature_can_pass_without_claiming_a_physical_test(self):
        self.engineering_surface()
        fixture.EngineeringHarnessTests.complete(self)
        result = self.h.validate(self.run, "release")
        self.assertTrue(result["passed"], result["errors"])

    def test_purpose_justified_actual_section_is_not_rejected_by_road_or_layer_quota(self):
        self.justified_section()
        fixture.EngineeringHarnessTests.complete(self)
        result = self.h.validate(self.run, "release")
        self.assertTrue(result["passed"], result["errors"])

    def test_engineering_basis_keeps_true_functional_cosmetic_or_noncritical_formation(self):
        self.engineering_surface()
        original = deepcopy(self.run)
        for formation in ("bridge", "native-support"):
            for cls in ("functional", "cosmetic", "noncritical"):
                with self.subTest(formation=formation, cls=cls):
                    self.run = deepcopy(original)
                    self.surface().update({"formation": formation, "class": cls,
                                           "noncritical_reason": "TEST ONLY classified from the complete purpose inventory"})
                    self.mark("surface-quality-strategy")
                    self.mark("supported-surface-quality")

    def test_design_accepts_a_process_plan_but_slice_requires_actual_toolpaths(self):
        self.engineering_surface()
        self.surface()["engineering_justification"].pop("toolpath_assessment")
        self.surface().pop("slice")
        self.run["plates"]["plate01"]["artifacts"] = []
        self.mark("surface-quality-strategy")
        with self.assertRaisesRegex(eh.HarnessError, "actual project and job|toolpath_assessment"):
            self.mark("supported-surface-quality")

    def test_supported_noncritical_alias_needs_the_same_engineering_basis(self):
        self.engineering_surface()
        self.surface().update({"class": "noncritical", "strategy": "assessed-noncritical",
                               "noncritical_reason": "TEST ONLY independently classified full feature scope"})
        self.mark("surface-quality-strategy")
        self.mark("supported-surface-quality")
        self.surface().pop("engineering_justification")
        with self.assertRaisesRegex(eh.HarnessError, "engineering requirement_basis"):
            self.mark("surface-quality-strategy")

    def test_supported_surface_cannot_escape_review_by_direct_print_or_class_rename(self):
        self.engineering_surface()
        original = deepcopy(self.run)
        for cls in ("functional", "cosmetic", "noncritical"):
            with self.subTest(cls=cls):
                self.run = deepcopy(original)
                self.surface().update({"class": cls, "strategy": "direct-print",
                                       "noncritical_reason": "TEST ONLY renamed class cannot establish actual quality"})
                with self.assertRaisesRegex(eh.HarnessError, "supported/bridge surface needs"):
                    self.mark("surface-quality-strategy")

    def test_engineering_observations_cannot_be_missing_unknown_or_generic_boolean(self):
        self.engineering_surface()
        original = deepcopy(self.run)
        fields = ("requirement_basis", "geometry_process_basis", "acceptance_budget", "toolpath_assessment")
        for field in fields:
            check = "supported-surface-quality" if field == "toolpath_assessment" else "surface-quality-strategy"
            for value in (None, True, "looks okay", {**self.observed(), "result": "unknown"},
                          {**self.observed(), "evidence": None}):
                with self.subTest(field=field, value=value):
                    self.run = deepcopy(original)
                    self.surface()["engineering_justification"][field] = value
                    with self.assertRaisesRegex(eh.HarnessError, field):
                        self.mark(check)

    def test_engineering_budget_requires_current_evidence_locator_and_row_citation(self):
        self.engineering_surface()
        path = self.root / "budget-proof.txt"
        path.write_text("TEST ONLY finite synthetic acceptance budget and applicability comparison\n")
        self.h.bind(self.run, "budget-proof", str(path), "evidence")
        self.surface()["engineering_justification"]["acceptance_budget"]["evidence"] = self.ref("budget-proof")
        original = deepcopy(self.run)
        for field, value in (("sha256", "0" * 64), ("locator", ""), ("artifact", "not-bound")):
            with self.subTest(field=field):
                self.run = deepcopy(original)
                self.surface()["engineering_justification"]["acceptance_budget"]["evidence"][field] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark("surface-quality-strategy")
        self.run = deepcopy(original)
        with self.assertRaisesRegex(eh.HarnessError, "must cite every structured"):
            self.mark("surface-quality-strategy", [k for k in self.run["artifacts"] if k != "budget-proof"])
        path.write_text("TEST ONLY changed synthetic budget after binding\n")
        with self.assertRaisesRegex(eh.HarnessError, "missing or changed file"):
            self.mark("surface-quality-strategy")

    def test_all_pass_stamps_cannot_replace_an_unresolved_engineering_acceptance_budget(self):
        self.engineering_surface()
        fixture.EngineeringHarnessTests.complete(self)
        self.surface()["engineering_justification"]["acceptance_budget"]["result"] = "unknown"
        for check, target in self.h.required(self.run, "release"):
            row = next(r for r in self.run["checks"] if r["id"] == check["id"] and r["target"] == target)
            row["basis_sha256"] = self.h.basis(self.run, check["stage"])
        result = self.h.validate(self.run, "release")
        self.assertFalse(result["passed"])
        self.assertTrue(any("engineering acceptance_budget" in e for e in result["errors"]))

    def test_engineering_slice_needs_every_actual_project_job_and_resolved_profile(self):
        self.engineering_surface()
        original = deepcopy(self.run)
        for absent in ("mesh", "project", "job", "machine", "filament", "process"):
            with self.subTest(absent=absent):
                self.run = deepcopy(original)
                if absent == "mesh":
                    self.run["parts"]["bracket"]["artifacts"] = []
                elif absent in ("project", "job"):
                    self.run["plates"]["plate01"]["artifacts"].remove(absent)
                else:
                    self.run["artifacts"].pop(absent)
                with self.assertRaisesRegex(eh.HarnessError, "current part geometry|actual project and job|resolved manufacturing profiles"):
                    self.mark("supported-surface-quality")

    def test_every_relevant_plate_requires_its_own_project_and_job(self):
        self.engineering_surface()
        self.run["plates"]["plate02"] = {"parts": ["bracket"], "artifacts": ["project"]}
        self.run["manufacturing_quality"]["plates"]["plate02"] = deepcopy(
            self.run["manufacturing_quality"]["plates"]["plate01"])
        with self.assertRaisesRegex(eh.HarnessError, "every relevant plate"):
            self.mark("supported-surface-quality")

    def test_physical_strategy_still_requires_a_real_test_even_after_noncritical_rename(self):
        self.surface().update({"class": "noncritical",
                               "noncritical_reason": "TEST ONLY classification does not manufacture a physical test"})
        self.surface().pop("physical_validation")
        with self.assertRaisesRegex(eh.HarnessError, "actual accepted physical test required"):
            self.mark("supported-surface-quality")

    def test_section_basis_does_not_relax_continuity_forming_base_or_seam(self):
        self.justified_section()
        original = deepcopy(self.run)
        for field, value in (("continuous", False), ("seam_safe", False),
                             ("base_supported", False), ("forming_base", "air")):
            with self.subTest(field=field):
                self.run = deepcopy(original)
                self.edge()[field] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark("free-edge-continuity")

    def test_section_basis_requires_actual_positive_counts_for_applicable_axes(self):
        self.justified_section()
        original = deepcopy(self.run)
        for kind, roads, layers in (("vertical-web", 2, None), ("horizontal-skin", None, 3), ("mixed", 2, 3)):
            with self.subTest(kind=kind):
                self.run = deepcopy(original)
                self.edge().update({"kind": kind, "min_roads": roads, "min_layers": layers})
                self.mark("free-edge-continuity")
                for field, applicable in (("min_roads", kind != "horizontal-skin"),
                                          ("min_layers", kind != "vertical-web")):
                    if not applicable:
                        continue
                    current = self.edge()[field]
                    for bad in (None, 0, -1, True, 2.0):
                        with self.subTest(field=field, bad=bad):
                            self.edge()[field] = bad
                            with self.assertRaisesRegex(eh.HarnessError, "honest positive actual"):
                                self.mark("free-edge-continuity")
                    self.edge()[field] = current

    def test_section_requirement_and_actual_formation_need_specific_current_observations(self):
        self.justified_section()
        original = deepcopy(self.run)
        for field in ("requirement_basis", "actual_section_formation"):
            for value in (None, {**self.observed(), "result": "unknown"},
                          {**self.observed(), "evidence": {**self.ref(), "sha256": "0" * 64}}):
                with self.subTest(field=field, value=value):
                    self.run = deepcopy(original)
                    self.edge()["section_justification"][field] = value
                    with self.assertRaisesRegex(eh.HarnessError, field):
                        self.mark("free-edge-continuity")

    def test_removing_section_basis_retains_the_unjustified_thin_section_fallback(self):
        self.justified_section()
        self.edge().pop("section_justification")
        with self.assertRaisesRegex(eh.HarnessError, "3 actual contiguous roads|4 actual continuous layers"):
            self.mark("free-edge-continuity")


if __name__ == "__main__":
    unittest.main()
