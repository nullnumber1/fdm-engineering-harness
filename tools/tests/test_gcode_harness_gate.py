"""Synthetic offline integration tests; no real job or approval is produced."""
from copy import deepcopy
import struct
import unittest
from zipfile import ZIP_STORED, ZipFile

import test_engineering_harness as fixture

eh = fixture.eh


class GcodeHarnessGateTests(unittest.TestCase):
    def setUp(self):
        fixture.EngineeringHarnessTests.setUp(self)

    def complete(self):
        fixture.EngineeringHarnessTests.complete(self)

    def review(self):
        return self.run["plates"]["plate01"]["gcode_review"]

    def mark(self, status="PASS", evidence=None):
        self.h.mark(self.run, "gcode-customization-audit", "plate:plate01", status,
                    "TEST ONLY synthetic source and continuation evidence; no physical certification",
                    self.run["owner"], "inspection",
                    ["job", "gcode-baseline", "gcode-scope"] if evidence is None else evidence,
                    "TEST ONLY source comparison and bounded body")

    def job(self, program):
        path = self.root / "job.gcode"
        path.write_text(program)
        self.h.bind(self.run, "job", str(path), "gcode", plate="plate01")

    def archive(self, members):
        path = self.root / "job.gcode.3mf"
        with ZipFile(path, "w", compression=ZIP_STORED) as archive:
            for name, program in members:
                archive.writestr(name, program)
        self.h.bind(self.run, "job", str(path), "gcode", plate="plate01")
        return path

    def modal_program(self, block):
        return ("; TEST ONLY synthetic modified native program\nG90\nM83\n; CHANGE_LAYER\n"
                "G1 X1 Y1 E.1 F1000\n" + block
                + "G1 X2 Y2 E.1 F1000\n; EXECUTABLE_BLOCK_END\n")

    def test_new_plate_defaults_to_unknown_and_check_is_mandatory(self):
        fresh = self.h.create("new-gcode-test", ["part"], ["plate"], "other-petg", "prototype")
        self.assertEqual(fresh["plates"]["plate"]["gcode_review"], {
            "customization": "unknown", "expected_e_mode": None,
            "scope_artifact": None, "baseline_artifact": None,
        })
        self.complete()
        self.run["checks"] = [r for r in self.run["checks"] if r["id"] != "gcode-customization-audit"]
        self.assertTrue(self.h.validate(self.run, "intake")["passed"])
        self.assertTrue(self.h.validate(self.run, "design")["passed"])
        for stage in ("slice", "release"):
            result = self.h.validate(self.run, stage)
            self.assertFalse(result["passed"])
            self.assertTrue(any("gcode-customization-audit@plate:plate01: missing check" in e for e in result["errors"]))

    def test_missing_malformed_or_unknown_metadata_blocks_slice_only(self):
        self.complete()
        original = deepcopy(self.run)
        bad = [None, {}, [], {**self.review(), "customization": "unknown"},
               {**self.review(), "customization": []}, {**self.review(), "expected_e_mode": None},
               {**self.review(), "expected_e_mode": []}, {**self.review(), "scope_artifact": None},
               {**self.review(), "baseline_artifact": None}]
        for metadata in bad:
            with self.subTest(metadata=metadata):
                self.run = deepcopy(original)
                self.run["plates"]["plate01"]["gcode_review"] = metadata
                self.assertTrue(self.h.validate(self.run, "intake")["passed"])
                self.assertTrue(self.h.validate(self.run, "design")["passed"])
                self.assertFalse(self.h.validate(self.run, "slice")["passed"])
                with self.assertRaises(eh.HarnessError):
                    self.mark()
        self.run = deepcopy(original)
        del self.run["plates"]["plate01"]["gcode_review"]
        self.assertFalse(self.h.validate(self.run, "slice")["passed"])

    def test_check_cannot_be_waived_for_unmodified_native_job(self):
        self.assertEqual(self.review()["customization"], "none")
        with self.assertRaisesRegex(eh.HarnessError, "N/A forbidden"):
            self.mark("N/A")

    def test_scope_baseline_and_all_final_jobs_must_be_cited(self):
        for omitted in ("gcode-scope", "gcode-baseline", "job"):
            with self.subTest(omitted=omitted), self.assertRaisesRegex(eh.HarnessError, "must cite every"):
                self.mark(evidence=[a for a in ("gcode-scope", "gcode-baseline", "job") if a != omitted])

    def test_native_baseline_cannot_alias_final_and_scope_cannot_alias_program(self):
        original = deepcopy(self.run)
        self.h.bind(self.run, "gcode-baseline", "job.gcode", "gcode-baseline")
        with self.assertRaisesRegex(eh.HarnessError, "separate immutable"):
            self.mark()
        self.run = deepcopy(original)
        self.h.bind(self.run, "gcode-scope", "gcode-baseline.gcode", "evidence")
        with self.assertRaisesRegex(eh.HarnessError, "separate origin"):
            self.mark()

    def test_none_requires_exact_program_payload_match(self):
        self.job(fixture.SYNTHETIC_GCODE.replace("E.1", "E.2"))
        with self.assertRaisesRegex(eh.HarnessError, "none declaration differs"):
            self.mark()
        self.review()["customization"] = "modified"
        self.mark()

    def test_modified_no_m83_or_m83_before_g90_is_rejected(self):
        self.review()["customization"] = "modified"
        for block in ("G91\nG1 Z.4 F600\nG90\n", "G91\nM83\nG90\n"):
            with self.subTest(block=block):
                self.job(self.modal_program(block))
                with self.assertRaisesRegex(eh.HarnessError, "narrow modal guard FAIL"):
                    self.mark()

    def test_unconditional_expected_mode_after_last_g90_allows_narrow_guard(self):
        self.review()["customization"] = "modified"
        self.job(self.modal_program("G91\nG1 Z.4 F600\nG1 Z-.4 F600\nG90\nM83\n"))
        self.complete()
        result = self.h.validate(self.run, "slice")
        self.assertTrue(result["passed"], result["errors"])
        self.assertTrue(self.h.validate(self.run, "release", str(self.root / "job.gcode"))["passed"])

    def test_conditional_only_restoration_blocks_with_unknown(self):
        self.review()["customization"] = "modified"
        self.job(self.modal_program("G90\nM622 J1\nM83\nM623\n"))
        with self.assertRaisesRegex(eh.HarnessError, "narrow modal guard UNKNOWN"):
            self.mark()

    def test_expected_mode_is_not_inferred_from_commands(self):
        self.review()["expected_e_mode"] = "absolute"
        with self.assertRaisesRegex(eh.HarnessError, "narrow modal guard FAIL"):
            self.mark()

    def test_packed_native_program_can_match_raw_baseline_with_container_changes(self):
        path = self.archive([("Metadata/plate_1.gcode", fixture.SYNTHETIC_GCODE),
                             ("Metadata/project_settings.config", '{"TEST ONLY":"new metadata"}')])
        self.complete()
        result = self.h.validate(self.run, "release", str(path))
        self.assertTrue(result["passed"], result["errors"])

    def test_all_embedded_programs_and_all_attached_jobs_are_audited(self):
        self.review()["customization"] = "modified"
        bad = self.modal_program("G90\n")
        self.archive([("Metadata/plate_1.gcode", fixture.SYNTHETIC_GCODE), ("Metadata/plate_2.gcode", bad)])
        with self.assertRaisesRegex(eh.HarnessError, "narrow modal guard FAIL"):
            self.mark()
        self.job(fixture.SYNTHETIC_GCODE)
        path = self.root / "second.gcode"
        path.write_text(bad)
        self.h.bind(self.run, "second-job", str(path), "gcode", plate="plate01")
        with self.assertRaisesRegex(eh.HarnessError, "second-job: narrow modal guard FAIL"):
            self.mark(evidence=["job", "second-job", "gcode-scope", "gcode-baseline"])

    def test_none_cannot_ignore_extra_or_swapped_archive_programs(self):
        self.archive([("Metadata/plate_1.gcode", fixture.SYNTHETIC_GCODE),
                      ("Metadata/plate_2.gcode", fixture.SYNTHETIC_GCODE)])
        with self.assertRaisesRegex(eh.HarnessError, "none declaration differs"):
            self.mark()
        baseline = self.root / "native-baseline.3mf"
        second = fixture.SYNTHETIC_GCODE.replace("E.1", "E.2")
        with ZipFile(baseline, "w") as archive:
            archive.writestr("Metadata/plate_1.gcode", fixture.SYNTHETIC_GCODE)
            archive.writestr("Metadata/plate_2.gcode", second)
        self.h.bind(self.run, "gcode-baseline", str(baseline), "gcode-baseline")
        self.archive([("Metadata/plate_1.gcode", second), ("Metadata/plate_2.gcode", fixture.SYNTHETIC_GCODE)])
        with self.assertRaisesRegex(eh.HarnessError, "none declaration differs"):
            self.mark()

    def test_empty_invalid_and_crc_corrupt_archives_fail_closed(self):
        for members in ([], [("Metadata/plate_1.gcode", "")]):
            with self.subTest(members=members):
                self.archive(members)
                with self.assertRaises(eh.HarnessError):
                    self.mark()
        path = self.archive([("Metadata/plate_1.gcode", fixture.SYNTHETIC_GCODE)])
        data = bytearray(path.read_bytes())
        # Corrupt one stored payload byte without updating the ZIP CRC fields.
        offset = 30 + struct.unpack_from("<H", data, 26)[0] + struct.unpack_from("<H", data, 28)[0]
        data[offset] ^= 1
        path.write_bytes(data)
        self.h.bind(self.run, "job", str(path), "gcode", plate="plate01")
        with self.assertRaisesRegex(eh.HarnessError, "CRC"):
            self.mark()
        path.write_bytes(b"TEST ONLY not a ZIP archive")
        self.h.bind(self.run, "job", str(path), "gcode", plate="plate01")
        with self.assertRaises(eh.HarnessError):
            self.mark()

    def test_scope_baseline_and_final_changes_require_new_checks(self):
        self.complete()
        original = deepcopy(self.run)
        for key in ("gcode-scope", "gcode-baseline", "job"):
            with self.subTest(key=key):
                self.run = deepcopy(original)
                artifact = self.run["artifacts"][key]
                path = self.root / artifact["path"]
                previous = path.read_text()
                path.write_text(previous + "; TEST ONLY changed evidence or program\n")
                self.assertFalse(self.h.validate(self.run, "slice")["passed"])
                self.h.bind(self.run, key, str(path), artifact["role"],
                            plate="plate01" if key == "job" else None)
                result = self.h.validate(self.run, "slice")
                self.assertFalse(result["passed"])
                self.assertTrue(any("stale review basis" in e or "missing or replaced evidence" in e for e in result["errors"]))
                self.assertTrue(self.h.validate(self.run, "intake")["passed"])
                path.write_text(previous)

    def test_gcode_metadata_change_stales_slice_and_preserves_design_basis(self):
        self.complete()
        self.review()["customization"] = "modified"
        self.assertTrue(self.h.validate(self.run, "intake")["passed"])
        self.assertTrue(self.h.validate(self.run, "design")["passed"])
        result = self.h.validate(self.run, "slice")
        self.assertFalse(result["passed"])
        self.assertTrue(any("stale review basis" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
