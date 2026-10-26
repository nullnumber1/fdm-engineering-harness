"""Synthetic schema regressions only. No real part/physical evidence or release."""
from copy import deepcopy
import unittest
import test_engineering_harness as fixture

eh = fixture.eh


class BulkEdgeSectionScopeTests(unittest.TestCase):
    def setUp(self):
        fixture.EngineeringHarnessTests.setUp(self)

    def ref(self, name="proof"):
        return {"artifact": name, "sha256": self.run["artifacts"][name]["sha256"],
                "locator": "TEST ONLY: complete actual edge domain and all forming layers"}

    def observed(self):
        return {"result": "accepted", "observation": "TEST ONLY full domain integral core and actual two skin roads; no product proof",
                "evidence": self.ref()}

    def edges(self):
        return self.run["manufacturing_quality"]["parts"]["bracket"]["edges"]

    def bulk(self):
        edge = self.edges()[0]
        edge.update({"id": "bulk-boundary", "kind": "mixed", "min_roads": 2, "min_layers": None,
                     "adjacent_faces": ["supported-lip"], "feature_ids": ["main-bulk"]})
        edge["section_scope"] = {
            "classification": "integral-bulk-boundary",
            "domain": {"part_id": "bracket", "edge_id": "bulk-boundary", "parameter_range": [0, 1],
                       "layer_start": edge["layer_start"], "layer_end": edge["layer_end"],
                       "surface_ids": ["supported-lip"], "feature_ids": ["main-bulk"],
                       "coverage": "entire-edge"},
            "current_artifacts": [self.ref(k) for k in ("mesh", "project", "job", "machine", "filament", "process")],
            "bulk_evidence": [self.ref()],
            "applicable_minima": {"thin_roads_required": False, "thin_layers_required": False},
            "thin_section_absence": {"vertical": self.observed(), "horizontal": self.observed()},
            "thin_feature_inventory": [],
            **{k: self.observed() for k in ("not_standalone_sheet", "integral_parent_connection",
                                          "not_loaded_thin_roof", "no_actual_thin_section", "full_domain_inventory")}}
        return edge

    def mark(self, refs=None):
        self.h.mark(self.run, "free-edge-continuity", "part:bracket", "PASS",
                    "TEST ONLY full synthetic edge domain observation, not real production evidence",
                    self.run["owner"], "inspection", list(self.run["artifacts"]) if refs is None else refs,
                    "TEST ONLY actual complete synthetic domain")

    def test_explicit_evidenced_integral_bulk_retains_honest_two_roads(self):
        self.bulk()
        self.mark()
        self.assertEqual(self.edges()[0]["min_roads"], 2)
        self.assertIsNone(self.edges()[0]["min_layers"])

    def test_legacy_two_road_mixed_edge_remains_strict(self):
        edge = self.edges()[0];edge["min_roads"] = 2
        with self.assertRaisesRegex(eh.HarnessError, "3 actual contiguous roads"):
            self.mark()

    def strict_feature(self, kind="vertical-web", relationship="adjoining-outside-domain"):
        edge = self.bulk()
        thin = deepcopy(edge)
        thin.pop("section_scope")
        thin.update({"id": "strict-thin", "kind": kind, "min_roads": 3, "min_layers": 4})
        self.edges().append(thin)
        edge["section_scope"]["thin_feature_inventory"] = [
            {"edge_id": thin["id"], "relationship": relationship, "evidence": self.ref()}]
        return edge, thin

    def test_adjoining_strict_thin_record_is_not_replaced_by_bulk_record(self):
        self.strict_feature()
        self.mark()

    def test_adjoining_purpose_justified_thin_record_is_assessed_separately_from_bulk(self):
        _, thin = self.strict_feature("mixed")
        thin.update({"min_roads": 2, "min_layers": 3,
                     "section_justification": {field: self.observed() for field in
                                               ("requirement_basis", "actual_section_formation")}})
        self.mark()
        thin["section_justification"]["requirement_basis"]["result"] = "unknown"
        with self.assertRaisesRegex(eh.HarnessError, "requirement_basis"):
            self.mark()

    def test_justified_thin_feature_inside_bulk_does_not_disappear_from_its_domain(self):
        _, thin = self.strict_feature("mixed", "within-domain")
        thin.update({"min_roads": 2, "min_layers": 3,
                     "section_justification": {field: self.observed() for field in
                                               ("requirement_basis", "actual_section_formation")}})
        with self.assertRaisesRegex(eh.HarnessError, "mixed thin/bulk"):
            self.mark()

    def test_in_domain_horizontal_toe_keeps_four_layers(self):
        edge, _ = self.strict_feature("horizontal-skin", "within-domain")
        section = edge["section_scope"]
        section["applicable_minima"]["thin_layers_required"] = True
        section["thin_section_absence"].pop("horizontal")
        edge["min_layers"] = 4
        self.mark()
        edge["min_layers"] = 3
        with self.assertRaisesRegex(eh.HarnessError, "4 actual continuous layers"):
            self.mark()

    def test_mixed_domain_cannot_hide_actual_thin_roof_root_or_foot(self):
        for feature in ("HEAD2.2-floor", "M4roof2.5", "M3-loaded-root", "M3-foot", "free-one-road-lip"):
            with self.subTest(feature=feature):
                self.setUp()
                edge, thin = self.strict_feature("vertical-web", "within-domain")
                thin["min_roads"] = 2
                with self.assertRaises(eh.HarnessError):
                    self.mark()
                thin["min_roads"] = 3
                with self.assertRaisesRegex(eh.HarnessError, "mixed thin/bulk"):
                    self.mark()
                edge["section_scope"]["applicable_minima"]["thin_roads_required"] = True
                edge["section_scope"]["thin_section_absence"].pop("vertical")
                with self.assertRaisesRegex(eh.HarnessError, "3 actual contiguous roads"):
                    self.mark()
                edge["min_roads"] = 3
                self.mark()

    def test_whole_actual_edge_scope_cannot_be_one_point_wrong_edge_or_partial_layers(self):
        edge = self.bulk();original = deepcopy(edge)
        for field, value in (("part_id", "other"), ("edge_id", "other"), ("parameter_range", [.5, .5]),
                             ("parameter_range", [0, .99]), ("parameter_range", [False, True]),
                             ("layer_start", 11), ("layer_end", 19), ("coverage", "representative-point"),
                             ("surface_ids", []), ("surface_ids", ["unknown-face"]), ("feature_ids", ["other"])):
            with self.subTest(field=field, value=value):
                edge.clear();edge.update(deepcopy(original));edge["section_scope"]["domain"][field] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark()

    def test_all_current_geometry_job_project_and_profiles_are_required(self):
        edge = self.bulk();original = deepcopy(edge)
        for name in ("mesh", "project", "job", "machine", "filament", "process"):
            with self.subTest(source=name):
                edge.clear();edge.update(deepcopy(original))
                refs = edge["section_scope"]["current_artifacts"]
                edge["section_scope"]["current_artifacts"] = [r for r in refs if r["artifact"] != name]
                with self.assertRaisesRegex(eh.HarnessError, "complete current"):
                    self.mark()
        edge.clear();edge.update(deepcopy(original))
        edge["section_scope"]["current_artifacts"].append(self.ref("proof"))
        with self.assertRaisesRegex(eh.HarnessError, "complete current"):
            self.mark()

    def test_each_relevant_plate_requires_its_own_project_and_job(self):
        self.bulk()
        self.run["plates"]["plate02"] = {"parts": ["bracket"], "artifacts": ["project"]}
        quality = self.run["manufacturing_quality"]["plates"]
        quality["plate02"] = deepcopy(quality["plate01"])
        with self.assertRaisesRegex(eh.HarnessError, "complete current"):
            self.mark()

    def test_stale_hash_locator_actual_file_or_outside_row_binding_rejects_bulk_scope(self):
        edge = self.bulk();original = deepcopy(edge)
        for field, value in (("sha256", "stale"), ("locator", ""), ("artifact", "not-bound")):
            with self.subTest(field=field):
                edge.clear();edge.update(deepcopy(original));edge["section_scope"]["bulk_evidence"][0][field] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark()
        edge.clear();edge.update(deepcopy(original))
        with self.assertRaisesRegex(eh.HarnessError, "must cite every structured"):
            self.mark([k for k in self.run["artifacts"] if k != "proof"])
        path = self.root / self.run["artifacts"]["proof"]["path"]
        path.write_text("TEST ONLY changed evidence after binding")
        with self.assertRaisesRegex(eh.HarnessError, "changed.*file"):
            self.mark()

    def test_acceptance_cannot_be_a_boolean_or_unknown_or_unbound_observation(self):
        edge = self.bulk();original = deepcopy(edge)
        for field in ("not_standalone_sheet", "integral_parent_connection", "not_loaded_thin_roof", "full_domain_inventory"):
            for value in (True, None, {"result": "unknown", "observation": "TEST ONLY unknown full scope", "evidence": self.ref()}):
                with self.subTest(field=field, value=value):
                    edge.clear();edge.update(deepcopy(original));edge["section_scope"][field] = value
                    with self.assertRaises(eh.HarnessError):
                        self.mark()
        edge.clear();edge.update(deepcopy(original))
        edge["section_scope"]["thin_section_absence"]["vertical"] = False
        with self.assertRaises(eh.HarnessError):
            self.mark()

    def test_empty_unknown_and_contradictory_minimum_claims_fail_closed(self):
        edge = self.bulk();original = deepcopy(edge)
        for value in (None, {}, {"thin_roads_required": False},
                      {"thin_roads_required": False, "thin_layers_required": "false"}):
            with self.subTest(value=value):
                edge.clear();edge.update(deepcopy(original));edge["section_scope"]["applicable_minima"] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark()
        edge.clear();edge.update(deepcopy(original))
        edge["section_scope"]["applicable_minima"]["thin_layers_required"] = True
        edge["min_layers"] = 4
        # A claim of "absent" while the axis is applicable is contradictory.
        with self.assertRaisesRegex(eh.HarnessError, "absence observations"):
            self.mark()

    def test_missing_self_unknown_duplicate_and_bulk_only_thin_references_reject(self):
        edge, thin = self.strict_feature();original = deepcopy(self.edges())
        for ident in ("missing", edge["id"], [], None):
            with self.subTest(ref=ident):
                self.edges()[:] = deepcopy(original);edge = self.edges()[0]
                edge["section_scope"]["thin_feature_inventory"][0]["edge_id"] = ident
                with self.assertRaises(eh.HarnessError):
                    self.mark()
        self.edges()[:] = deepcopy(original);edge, thin = self.edges()
        edge["section_scope"]["thin_feature_inventory"] *= 2
        with self.assertRaises(eh.HarnessError):
            self.mark()
        self.edges()[:] = deepcopy(original);edge, thin = self.edges()
        thin["section_scope"] = deepcopy(edge["section_scope"])
        thin["section_scope"]["thin_feature_inventory"] = [{"edge_id": edge["id"], "relationship": "within-domain", "evidence": self.ref()}]
        with self.assertRaisesRegex(eh.HarnessError, "never self/cyclic/bulk-only"):
            self.mark()

    def test_continuity_seam_and_forming_base_always_remain_required(self):
        edge = self.bulk();original = deepcopy(edge)
        for field, value in (("continuous", False), ("seam_safe", False), ("base_supported", None),
                             ("forming_base", "air"), ("min_roads", None), ("min_layers", -1)):
            with self.subTest(field=field):
                edge.clear();edge.update(deepcopy(original));edge[field] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark()

    def test_malformed_nested_scope_fails_without_crashing(self):
        edge = self.bulk();original = deepcopy(edge)
        for field, value in (("domain", []), ("domain", None), ("bulk_evidence", []),
                             ("thin_feature_inventory", None), ("current_artifacts", [["bad"]]),
                             ("current_artifacts", [{"artifact": ["bad"]}])):
            with self.subTest(field=field):
                edge.clear();edge.update(deepcopy(original));edge["section_scope"][field] = value
                with self.assertRaises(eh.HarnessError):
                    self.mark()


if __name__ == "__main__":
    unittest.main()
