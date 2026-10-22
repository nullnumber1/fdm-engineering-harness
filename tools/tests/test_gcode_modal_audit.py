"""Synthetic offline regressions; no project G-code or printer is modified."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


MODULE_PATH = Path(__file__).resolve().parents[1] / "gcode_modal_audit.py"
SPEC = importlib.util.spec_from_file_location("gcode_modal_audit", MODULE_PATH)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def program(body, mode="M83", marker="CHANGE_LAYER"):
    return "G90\n%s\n; %s\nG1 X1 E.2\n%s\n; EXECUTABLE_BLOCK_END\n" % (mode, marker, body)


class ModalAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "final.gcode"

    def tearDown(self):
        self.temp.cleanup()

    def audit(self, text, expected="relative"):
        self.path.write_text(text, encoding="utf-8")
        return guard.audit_path(self.path, expected)

    def codes(self, report):
        return {i["code"] for i in report["issues"]}

    def test_known_temperature_band_regression_at_7_2(self):
        text = program("; Z_HEIGHT: 7.2\nM400\nG91\nG1 Z.6 F900\nG90\nM109 S250\nG91\nG1 Z-.6 F900\nG90\nG1 X2 Y2 E.026")
        report = self.audit(text)
        self.assertEqual(report["status"], "FAIL")
        first = next(i for i in report["issues"] if i["status"] == "FAIL")
        self.assertEqual(first["code"], "missing-explicit-e-mode")
        self.assertEqual(first["line"], 14)
        self.assertIn("Z_HEIGHT: 7.2", text)
        self.assertTrue(any(c["text"] == "G90" for c in first["context"]))

    def test_restore_after_last_coordinate_switch(self):
        report = self.audit(program("G91\nG1 Z.6\nG90\nM109 S250\nG91\nG1 Z-.6\nG90\nM83\nG1 X2 E.2"))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["members"][0]["coordinate_mode_switch_count"], 4)

    def test_restore_before_last_g90_is_insufficient(self):
        report = self.audit(program("G91\nM83\nG90\nG1 X2 E.2"))
        self.assertEqual(report["status"], "FAIL")

    def test_g92_origin_reset_does_not_restore_mode(self):
        report = self.audit(program("G90\nG92 E0\nG1 X2 E.2"))
        self.assertEqual(report["status"], "FAIL")

    def test_conditional_m83_does_not_restore_unconditionally(self):
        report = self.audit(program("G90\nM622 J1\nM83\nM623\nG1 X2 E.2"))
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertIn("conditional-e-mode", self.codes(report))

    def test_unconditional_restoration_after_conditional_can_pass(self):
        report = self.audit(program("M622 J1\nG90\nM623\nM83\nG1 X2 E.2"))
        self.assertEqual(report["status"], "PASS")

    def test_identical_safe_conditional_paths_pass_narrow_invariant(self):
        report = self.audit(program("M622 J1\nG90\nM83\nM622 J0\nG90\nM83\nM623\nM623\nG1 X2 E.2"))
        self.assertEqual(report["status"], "PASS")

    def test_native_object_masks_and_nested_flags_preserve_safe_e_mode(self):
        for mask in ("CAAAAAAAAAA=", "/wMAAAAAAAA=", "AAAAAAAAAIA="):
            with self.subTest(mask=mask):
                body = "M624 %s\nM622 J1\nG90\nM83\nM623\nG1 E.2\nM625\nG1 E.2" % mask
                self.assertEqual(self.audit(program(body))["status"], "PASS")

    def test_object_skip_cannot_prove_conditional_mode_restoration(self):
        body = "G90\nM624 CAAAAAAAAAA=\nM83\nM625\nG1 E.2"
        report = self.audit(program(body))
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertIn("conditional-e-mode", self.codes(report))

    def test_missing_e_mode_in_executed_object_path_still_fails(self):
        body = "M624 CAAAAAAAAAA=\nG90\nG1 E.2\nM625\nM83\nG1 E.2"
        report = self.audit(program(body))
        self.assertNotEqual(report["status"], "PASS")
        self.assertIn("conditional-e-mode", self.codes(report))

    def test_unconditional_e_assertion_after_object_skip_restores_narrow_proof(self):
        body = "M624 CAAAAAAAAAA=\nG90\nM625\nM83\nG1 E.2"
        self.assertEqual(self.audit(program(body))["status"], "PASS")

    def test_native_object_masks_reject_noncanonical_or_injected_arguments(self):
        masks = ("AAAAAAAAAAA=", "CAAAAAAAAAA", "CAAAAAAAAAA==", "CAAAAAAAAAA= S1",
                 "CAAAAAAAAAA=G90", "CAAAAAAAAAA= M83", "CAAAAAAAAAA= M98P1",
                 "CAAAAAAAAAA!", "CAAAAAAAAAB=", "AQ==", "", "-AAAAAAAAAA=")
        for mask in masks:
            with self.subTest(mask=mask):
                report = self.audit(program("M624 %s\nG1 E.2\nM625" % mask))
                self.assertNotEqual(report["status"], "PASS")
                self.assertIn("unsupported-object-mask", self.codes(report))

    def test_object_and_flag_blocks_must_be_properly_typed_and_balanced(self):
        bodies = ("M624 CAAAAAAAAAA=\nG1 E.2", "M625\nG1 E.2",
                  "M624 CAAAAAAAAAA=\nM623\nG1 E.2",
                  "M622 J1\nM625\nG1 E.2",
                  "M624 CAAAAAAAAAA=\nM622 J1\nM625\nM623\nG1 E.2",
                  "M624 CAAAAAAAAAA=\nM625 S1\nG1 E.2")
        for body in bodies:
            with self.subTest(body=body):
                report = self.audit(program(body))
                self.assertEqual(report["status"], "UNKNOWN")
                self.assertIn("unbalanced-conditional", self.codes(report))

    def test_unbalanced_conditional_blocks_pass(self):
        for body in ("M622 J1\nM83\nG1 E.1", "M623\nG1 E.1"):
            with self.subTest(body=body):
                report = self.audit(program(body))
                self.assertEqual(report["status"], "UNKNOWN")

    def test_absolute_profile_requires_m82_not_m83(self):
        self.assertEqual(self.audit(program("G90\nM82\nG1 E1", mode="M82"), "absolute")["status"], "PASS")
        self.assertEqual(self.audit(program("G90\nM83\nG1 E1", mode="M82"), "absolute")["status"], "FAIL")

    def test_temperature_only_modification_does_not_need_extra_mode_switch(self):
        self.assertEqual(self.audit(program("M104 S245\nM109 S245\nG1 X2 E.3"))["status"], "PASS")

    def test_vendor_flag_names_are_not_gcode_commands(self):
        report = self.audit(program("M1002 judge_flag g39_3rd_layer_detect_flag\nM622.1 S1\nG1 E.2"))
        self.assertEqual(report["status"], "PASS")

    def test_no_initial_assertion_is_not_pass(self):
        report = self.audit("; CHANGE_LAYER\nG1 X1 E.2\n; EXECUTABLE_BLOCK_END\n")
        self.assertNotEqual(report["status"], "PASS")

    def test_no_printing_e_or_missing_bounds_is_unknown(self):
        for text in ("G90\nM83\nG1 E.1\n", "M83\n; CHANGE_LAYER\nG1 X1\n; EXECUTABLE_BLOCK_END\n",
                     "M83\n; CHANGE_LAYER\nG1 E-.1\n; EXECUTABLE_BLOCK_END\n"):
            with self.subTest(text=text):
                self.assertEqual(self.audit(text)["status"], "UNKNOWN")

    def test_comments_and_compact_motion_and_line_numbers(self):
        text = "G90\nM83\n; LAYER_CHANGE\n; G90\n(G91)\nN12 G1X1Y2E.2 (M82) ; G90\n; filament end gcode\nG90\nG1 E-1\n"
        self.assertEqual(self.audit(text)["status"], "PASS")

    def test_unsupported_syntax_blocks_pass(self):
        for body in ("G1 X1 E{amount}", "G1 E.2*42", "G90 M83\nG1 E.2", "M83G1E.2", "M83 X1", "G1 E.2 (unclosed", "X1 E.2", "G1 E.1 E.2", "M98 P123"):
            with self.subTest(body=body):
                report = self.audit(program(body))
                self.assertNotEqual(report["status"], "PASS")

    def test_compact_multiple_commands_after_nonmodal_commands_are_unknown(self):
        for body in ("M104S250G90G1E.2", "M622J1G90M83\nM623",
                     "M622 J1\nM83\nM623G90G1E.2", "M104 S250G90bad"):
            with self.subTest(body=body):
                report = self.audit(program(body + "\nG1 E.2"))
                self.assertEqual(report["status"], "UNKNOWN")

    def test_prefix_macro_or_state_stack_invalidates_mode_proof(self):
        for command in ("M98 P123", "M99", "M120", "M121"):
            with self.subTest(command=command):
                text = "M83\n%s\n; CHANGE_LAYER\nG1 E.2\n; EXECUTABLE_BLOCK_END\n" % command
                report = self.audit(text)
                self.assertEqual(report["status"], "UNKNOWN")
                self.assertIn("unresolved-state-control", self.codes(report))

    def test_explicit_assertion_after_prefix_macro_restores_narrow_proof(self):
        text = "M83\nM98 P123\nM83\n; CHANGE_LAYER\nG1 E.2\n; EXECUTABLE_BLOCK_END\n"
        self.assertEqual(self.audit(text)["status"], "PASS")

    def test_report_hashes_input_profile_and_member(self):
        profile = self.root / "resolved.json"
        profile.write_text('{"use_relative_e_distances": true}', encoding="utf-8")
        self.audit(program("G1 X2 E.2"))
        report = guard.audit_path(self.path, "relative", profile)
        expected = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(report["container_sha256"], expected)
        self.assertEqual(report["members"][0]["sha256"], expected)
        self.assertEqual(report["profile"]["sha256"], hashlib.sha256(profile.read_bytes()).hexdigest())
        self.assertTrue(report["limitations"])

    def archive(self, members):
        path = self.root / "job.gcode.3mf"
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in members:
                archive.writestr(name, data)
        return guard.audit_path(path, "relative")

    def test_all_gcode_archive_members_are_checked(self):
        report = self.archive([("Metadata/plate_1.gcode", program("G1 E.2")),
                               ("Metadata/plate_2.gcode", program("G90\nG1 E.2")),
                               ("Metadata/model.config", "opaque model metadata")])
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(len(report["members"]), 2)
        self.assertEqual(report["members"][1]["status"], "FAIL")
        self.assertTrue(report["container_sha256"])

    def test_archive_empty_binary_and_duplicate_members_are_unknown(self):
        for members in ([("model.stl", "not toolpath")],
                        [("a.gcode", program("G1 E.2")), ("b.gcode", b"\x00\xff")]):
            with self.subTest(members=members):
                self.assertEqual(self.archive(members)["status"], "UNKNOWN")
        with self.assertWarns(UserWarning):
            report = self.archive([("a.gcode", program("G1 E.2")), ("a.gcode", program("G1 E.2"))])
        self.assertEqual(report["status"], "UNKNOWN")

    def test_nontext_corrupt_archive_missing_input_invalid_mode_are_unknown(self):
        self.path.write_bytes(b"\x00\xff")
        self.assertEqual(guard.audit_path(self.path, "relative")["status"], "UNKNOWN")
        path = self.root / "broken.3mf"
        path.write_bytes(b"not zip")
        self.assertEqual(guard.audit_path(path, "relative")["status"], "UNKNOWN")
        self.assertEqual(guard.audit_path(self.root / "missing.gcode", "relative")["status"], "UNKNOWN")
        self.assertEqual(guard.audit_path(self.path, "wrong")["status"], "UNKNOWN")

    def test_output_requires_new_file_and_cannot_alias_input(self):
        text = program("G1 E.2")
        self.audit(text)
        output = self.root / "report.json"
        self.assertEqual(guard.main([str(self.path), "--expected-e-mode", "relative", "--output", str(output)]), 0)
        self.assertEqual(json.loads(output.read_text())["status"], "PASS")
        for target in (output, self.path):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                guard.main([str(self.path), "--expected-e-mode", "relative", "--output", str(target)])
        self.assertEqual(self.path.read_text(), text)
        alias = self.root / "alias.gcode"
        alias.symlink_to(self.path)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            guard.main([str(self.path), "--expected-e-mode", "relative", "--output", str(alias)])

    def test_cli_nonpass_is_nonzero_and_mode_is_required(self):
        self.audit(program("G90\nG1 E.2"))
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            code = guard.main([str(self.path), "--expected-e-mode", "relative"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stream.getvalue())["status"], "FAIL")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            guard.main([str(self.path)])


if __name__ == "__main__":
    unittest.main()
