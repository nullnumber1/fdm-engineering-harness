"""Synthetic offline fixtures test the gate, not any actual engineering release."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("engineering_harness", REPO / "tools/engineering_harness.py")
eh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eh)
SYNTHETIC_GCODE = ("; SYNTHETIC TEST FIXTURE ONLY; NO ACTUAL PRINT\n"
                   "G90\nM83\n; CHANGE_LAYER\nG1 X1 Y1 E.1\n; EXECUTABLE_BLOCK_END\n")


def install_synthetic_quality(run, harness):
    """Fictional observations exercise schemas; they are never actual evidence."""
    def ref(key):
        return {"artifact": key, "sha256": run["artifacts"][key]["sha256"],
                "locator": "TEST ONLY: fictional measured feature and exact layer range"}

    def observed():
        return {"result": "accepted", "observation": "TEST ONLY fictional physical observation; no real manufacturing claim",
                "evidence": ref("proof")}

    surface = {"id": "supported-lip", "class": "functional", "formation": "native-support",
               "acceptance": "TEST ONLY fictional no-holes and flatness criterion", "area_mm2": 500.0,
               "max_span_mm": 15.0, "strategy": "physically-validated", "evidence": ref("proof"),
               "slice": {"first_model_z_mm": 10.0, "unsupported_span_mm": 0.5,
                         "interface_gap_mm": 0.2, "interface_pitch_mm": 0.5,
                         "anchoring": "TEST ONLY fictional two-sided anchoring",
                         "line_direction": "TEST ONLY fictional short direction",
                         "edge_formation": "TEST ONLY fictional continuous formed edge", "evidence": ref("proof")},
               "physical_validation": {"source": "physical-test", "result": "accepted",
                   "test_actor": "SYNTHETIC FICTIONAL TESTER", "sample_id": "SYNTHETIC-SAMPLE-ONLY",
                   "observed_at": "SYNTHETIC TIME ONLY", "material_condition": "TEST ONLY fictional dry material condition",
                   "process_signature": harness.quality_process_signature(run), "test_kind": "representative-coupon",
                   "equivalence": "TEST ONLY fictional matching geometry, orientation, span and forming edge",
                   "geometry_evidence": ref("mesh"), "project_equivalence_evidence": ref("proof"),
                   "criteria": {k: observed() for k in ("surface-finish", "dimensional-integrity", "layer-bonding", "edge-curl", "removability")}}}
    edge = {"id": "lip-edge", "kind": "mixed", "layer_start": 10, "layer_end": 20,
            "min_roads": 3, "min_layers": 4, "forming_base": "native-support", "continuous": True,
            "seam_safe": True, "base_supported": True, "evidence": ref("proof"),
            "observation": "TEST ONLY fictional continuous roads, forming base and safe seam at all edge layers"}
    group = {"id": "normal-group", "part_id": "bracket", "surface_ids": ["supported-lip"],
             **{k: observed() for k in ("root_stability", "interface_coverage", "model_edge_curl", "nozzle_collision", "removal_access")}}
    run["manufacturing_quality"] = {"schema_version": 1, "calibration_scope": None,
        "parts": {"bracket": {"inventory_evidence": ref("proof"), "surfaces": [surface], "edges": [edge]}},
        "plates": {"plate01": {"inventory_evidence": ref("proof"), "has_supports": True, "support_groups": [group]}}}


class EngineeringHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in eh.POLICY_FILES:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((REPO / name).read_bytes())
        self.h = eh.Harness(self.root)
        self.run = self.h.create("test-only", ["bracket"], ["plate01"],
                                 "bambu-petg-basic", "production")
        for key, role, suffix in (
            ("source", "source", ".py"), ("mesh", "geometry", ".stl"),
            ("machine", "machine-profile", ".json"), ("filament", "filament-profile", ".json"),
            ("process", "process-profile", ".json"), ("project", "project", ".3mf"),
            ("job", "gcode", ".gcode"), ("proof", "evidence", ".txt"),
            ("gcode-baseline", "gcode-baseline", ".gcode"), ("gcode-scope", "evidence", ".md"),
            ("components-baseline", "component-baseline", ".md"),
            ("components-comparison", "evidence", ".md"),
        ):
            path = self.root / (key + suffix)
            path.write_text(SYNTHETIC_GCODE if role in {"gcode", "gcode-baseline"}
                            else "SYNTHETIC TEST FIXTURE ONLY; NO REAL ENGINEERING ASSESSMENT\n")
            self.h.bind(self.run, key, str(path), role,
                        "bracket" if role == "geometry" else None,
                        "plate01" if role in {"project", "gcode"} else None)
        register = self.root / eh.COMPONENT_REGISTER
        register.parent.mkdir(parents=True, exist_ok=True)
        register.write_text("SYNTHETIC TEST COMPONENT REGISTER ONLY; NO REAL ASSEMBLY INVENTORY\n")
        self.h.bind(self.run, "components-register", eh.COMPONENT_REGISTER, "component-register")
        self.run["component_control"].update({"register_artifact": "components-register",
                                              "baseline_artifact": "components-baseline",
                                              "comparison_artifact": "components-comparison"})
        self.run["plates"]["plate01"]["gcode_review"] = {
            "customization": "none", "expected_e_mode": "relative",
            "scope_artifact": "gcode-scope", "baseline_artifact": "gcode-baseline",
        }
        install_synthetic_quality(self.run, self.h)

    def complete(self, run=None):
        run = self.run if run is None else run
        if run["component_control"]["decision"] == "unknown":
            run["component_control"]["decision"] = "unchanged"
        for c, target in self.h.required(run, "release"):
            independent = c["id"] == "independent-review"
            evidence = ["proof"]
            if c["id"] in eh.COMPONENT_CHECKS:
                evidence += ["components-register", "components-baseline", "components-comparison"]
            if c["id"] == "gcode-customization-audit":
                plate = run["plates"][target.split(":", 1)[1]]
                evidence += [a for a in plate["artifacts"] if run["artifacts"][a]["role"] == "gcode"]
                evidence += [plate["gcode_review"]["scope_artifact"], plate["gcode_review"]["baseline_artifact"]]
            if c["id"] in eh.QUALITY_CHECKS:
                evidence = ["proof", "mesh"] if c["stage"] == "design" else list(run["artifacts"])
            self.h.mark(run, c["id"], target, "PASS", "Synthetic fixture observation; not a real release",
                        "review-agent" if independent else run["owner"],
                        "independent-review" if independent else "inspection", evidence,
                        "TEST ONLY: synthetic fixture")

    def test_new_run_blocks_every_stage(self):
        for stage in eh.STAGES:
            self.assertFalse(self.h.validate(self.run, stage)["passed"])

    def test_current_complete_review_passes_and_exact_job_matches(self):
        self.complete()
        result = self.h.validate(self.run, "release", str(self.root / "job.gcode"))
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["checks_required"], len(self.h.catalog))

    def test_missing_check_blocks_release(self):
        self.complete()
        self.run["checks"] = self.run["checks"][1:]
        self.assertFalse(self.h.validate(self.run, "release")["passed"])

    def test_native_supports_review_cannot_be_omitted_or_waived(self):
        self.complete()
        self.run["checks"] = [r for r in self.run["checks"] if r["id"] != "native-supports-only"]
        for stage in ("design", "slice", "release"):
            result = self.h.validate(self.run, stage)
            self.assertFalse(result["passed"])
            self.assertTrue(any("native-supports-only@part:bracket: missing check" in e
                                for e in result["errors"]))
        with self.assertRaises(eh.HarnessError):
            self.h.mark(self.run, "native-supports-only", "part:bracket", "N/A",
                        "Synthetic fixture: no support was needed", "main-session",
                        "inspection", ["proof"], "TEST ONLY body inventory")
        self.h.mark(self.run, "native-supports-only", "part:bracket", "FAIL",
                    "Synthetic fixture: custom support body present", "main-session",
                    "inspection", ["proof"], "TEST ONLY body inventory")
        self.assertFalse(self.h.validate(self.run, "design")["passed"])

    def test_each_part_and_plate_requires_own_checks(self):
        self.complete()
        self.run["parts"]["second"] = {"artifacts": ["mesh"]}
        self.run["plates"]["plate02"] = {"parts": ["second"], "artifacts": ["project", "job"]}
        result = self.h.validate(self.run, "release")
        missing = [e for e in result["errors"] if "missing check" in e]
        self.assertTrue(any("part:second" in e for e in missing))
        self.assertTrue(any("plate:plate02" in e for e in missing))

    def test_changed_geometry_and_rebind_still_require_new_assessment(self):
        self.complete()
        (self.root / "mesh.stl").write_text("MODIFIED TEST GEOMETRY")
        self.assertFalse(self.h.validate(self.run, "design")["passed"])
        self.h.bind(self.run, "mesh", "mesh.stl", "geometry", part="bracket")
        self.assertTrue(self.h.validate(self.run, "intake")["passed"])
        self.assertFalse(self.h.validate(self.run, "design")["passed"])

    def test_changed_project_only_invalidates_slice_and_later(self):
        self.complete()
        (self.root / "project.3mf").write_text("MODIFIED TEST LAYOUT")
        self.h.bind(self.run, "project", "project.3mf", "project", plate="plate01")
        self.assertTrue(self.h.validate(self.run, "design")["passed"])
        self.assertFalse(self.h.validate(self.run, "slice")["passed"])

    def test_changed_profile_invalidates_intake(self):
        self.complete()
        (self.root / "filament.json").write_text("MODIFIED TEST FILAMENT")
        self.h.bind(self.run, "filament", "filament.json", "filament-profile")
        self.assertFalse(self.h.validate(self.run, "intake")["passed"])

    def test_changed_evidence_or_rebinding_it_invalidates_rows(self):
        self.complete()
        (self.root / "proof.txt").write_text("ALTERED TEST EVIDENCE")
        self.assertFalse(self.h.validate(self.run, "release")["passed"])
        self.h.bind(self.run, "proof", "proof.txt", "evidence")
        self.assertFalse(self.h.validate(self.run, "release")["passed"])

    def test_changed_policy_invalidates_all_prior_reviews(self):
        self.complete()
        p = self.root / "AGENTS.md"
        p.write_text(p.read_text() + "\nChanged test policy\n")
        self.assertFalse(self.h.validate(self.run, "intake")["passed"])

    def test_pass_without_evidence_or_locator_rejected(self):
        c, target = self.h.required(self.run, "intake")[0]
        for evidence, locator in (([], "section"), (["proof"], "")):
            with self.assertRaises(eh.HarnessError):
                self.h.mark(self.run, c["id"], target, "PASS", "Synthetic fixture observation",
                            "main-session", "inspection", evidence, locator)

    def test_na_requires_permission_and_evidence(self):
        c = next(c for c in self.h.catalog if not c["na_allowed"])
        target = "run" if c["scope"] == "run" else f"{c['scope']}:{'bracket' if c['scope'] == 'part' else 'plate01'}"
        with self.assertRaises(eh.HarnessError):
            self.h.mark(self.run, c["id"], target, "N/A", "Synthetic fixture observation",
                        "main-session", "scope", ["proof"], "section")
        c = next(c for c in self.h.catalog if c["na_allowed"])
        target = "run" if c["scope"] == "run" else f"{c['scope']}:{'bracket' if c['scope'] == 'part' else 'plate01'}"
        with self.assertRaises(eh.HarnessError):
            self.h.mark(self.run, c["id"], target, "N/A", "Synthetic fixture observation",
                        "main-session", "scope", [], "section")

    def test_owner_cannot_sign_independent_review(self):
        with self.assertRaises(eh.HarnessError):
            self.h.mark(self.run, "independent-review", "run", "PASS", "Synthetic fixture observation",
                        self.run["owner"], "independent-review", ["proof"], "section")

    def test_duplicate_unknown_and_fail_rows_are_rejected(self):
        self.complete()
        original = deepcopy(self.run)
        self.run["checks"].append(deepcopy(self.run["checks"][0]))
        self.assertFalse(self.h.validate(self.run, "release")["passed"])
        for status in ("FAIL", "UNKNOWN", "skipped"):
            run = deepcopy(original)
            run["checks"][0]["status"] = status
            self.assertFalse(self.h.validate(run, "release")["passed"])

    def test_unassigned_part_or_missing_final_job_blocks(self):
        self.complete()
        self.run["plates"]["plate01"]["parts"] = []
        self.assertFalse(self.h.validate(self.run, "release")["passed"])
        self.run["plates"]["plate01"]["parts"] = ["bracket"]
        self.run["plates"]["plate01"]["artifacts"] = ["project"]
        self.assertFalse(self.h.validate(self.run, "release")["passed"])

    def test_wrong_exact_artifact_cannot_use_another_files_review(self):
        self.complete()
        other = self.root / "different.gcode"
        other.write_text("DIFFERENT TEST FILE")
        self.assertFalse(self.h.validate(self.run, "release", str(other))["passed"])

    def test_external_evidence_and_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            other = Path(external) / "proof.txt"
            other.write_text("external")
            with self.assertRaises(eh.HarnessError):
                self.h.bind(self.run, "outside", str(other), "evidence")
            (self.root / "escape.txt").symlink_to(other)
            with self.assertRaises(eh.HarnessError):
                self.h.bind(self.run, "outside", "escape.txt", "evidence")

    def test_sliced_archive_must_contain_toolpaths(self):
        self.complete()
        archive = self.root / "job.3mf"
        with ZipFile(archive, "w") as z:
            z.writestr("Metadata/project_settings.config", "{}")
        self.h.bind(self.run, "job", "job.3mf", "gcode", plate="plate01")
        with self.assertRaises(eh.HarnessError):
            self.complete()
        self.assertFalse(self.h.validate(self.run, "release", str(archive))["passed"])
        with ZipFile(archive, "w") as z:
            z.writestr("Metadata/plate_1.gcode", SYNTHETIC_GCODE)
        self.h.bind(self.run, "job", "job.3mf", "gcode", plate="plate01")
        self.complete()
        self.assertTrue(self.h.validate(self.run, "release", str(archive))["passed"])

    def test_material_identity_cannot_silently_change(self):
        self.complete()
        self.run["profile"]["material"]["product"] = "Bambu PETG HF"
        self.assertFalse(self.h.validate(self.run, "intake")["passed"])
        generic = self.h.create("generic-test", ["a"], ["one"], "other-petg", "production")
        self.assertEqual(generic["profile"]["material"]["variant"], "other-petg")
        self.assertEqual(generic["profile"]["material"]["manufacturer"], "unknown")

    def test_checklist_marks_stale_as_unchecked(self):
        self.complete()
        output = self.h.checklist(self.run)
        self.assertIn("[x]", output)
        (self.root / "mesh.stl").write_text("MODIFIED TEST GEOMETRY")
        self.h.bind(self.run, "mesh", "mesh.stl", "geometry", part="bracket")
        output = self.h.checklist(self.run)
        self.assertIn("[ ]", output)
        self.assertIn("STALE OR INVALID", output)

    def test_generated_output_cannot_overwrite_policy_or_bound_artifacts(self):
        original = (self.root / "AGENTS.md").read_bytes()
        for name in ("AGENTS.md", ".agents/skills/fdm-design/SKILL.md", "mesh.stl", "proof.txt"):
            with self.assertRaises(eh.HarnessError):
                self.h.write_markdown(name, self.h.catalog_markdown(), self.run)
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), original)
        bound = self.root / "bound-proof.md"
        bound.write_text(eh.GENERATED_MARKER + "\nDO NOT REPLACE BOUND EVIDENCE")
        self.h.bind(self.run, "bound", "bound-proof.md", "evidence")
        with self.assertRaises(eh.HarnessError):
            self.h.write_markdown("bound-proof.md", self.h.catalog_markdown(), self.run)

    def test_generated_output_only_overwrites_its_own_unbound_markdown(self):
        other = self.root / "notes.md"
        other.write_text("Existing unowned notes")
        with self.assertRaises(eh.HarnessError):
            self.h.write_markdown("notes.md", self.h.catalog_markdown())
        self.assertEqual(other.read_text(), "Existing unowned notes")
        path = self.h.write_markdown("checklist.md", self.h.catalog_markdown())
        self.h.write_markdown("checklist.md", self.h.catalog_markdown())
        self.assertTrue(path.read_text().startswith(eh.GENERATED_MARKER))
        with self.assertRaises(eh.HarnessError):
            self.h.write_markdown("new-model.stl", self.h.catalog_markdown())

    def test_catalog_cannot_overwrite_evidence_bound_in_any_registered_run(self):
        path = self.h.write_markdown("generated.md", self.h.catalog_markdown())
        path.write_text(path.read_text() + "\nTEST ONLY review annotation\n")
        self.h.bind(self.run, "generated-proof", "generated.md", "evidence")
        eh.atomic_json(self.root / "harness/runs/registered.json", self.run)
        original = path.read_bytes()
        with self.assertRaises(eh.HarnessError):
            self.h.write_markdown("generated.md", self.h.catalog_markdown())
        self.assertEqual(path.read_bytes(), original)
        other = self.h.create("other", ["a"], ["one"], "other-petg", "production")
        with self.assertRaises(eh.HarnessError):
            self.h.write_markdown("generated.md", self.h.catalog_markdown(), other)

    def test_run_registry_and_output_protection_fail_closed(self):
        for path in ("outside.json", "harness/runs/not-json.md"):
            with self.assertRaises(eh.HarnessError):
                self.h.review_path(path)
        eh.atomic_json(self.root / "harness/runs/broken.json", {"unrecognized": True})
        with self.assertRaises(eh.HarnessError):
            self.h.write_markdown("new.md", self.h.catalog_markdown())


if __name__ == "__main__":
    unittest.main()
