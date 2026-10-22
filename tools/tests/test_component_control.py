"""Synthetic component-change records exercise authorization gates, never authorize work."""
from copy import deepcopy
import unittest

import test_engineering_harness as fixture

eh = fixture.eh


class ComponentControlTests(unittest.TestCase):
    def setUp(self):
        fixture.EngineeringHarnessTests.setUp(self)

    def complete_unchanged(self):
        fixture.EngineeringHarnessTests.complete(self)

    def evidence_file(self, key, content=None):
        path = self.root / f"{key}.md"
        path.write_text(content or f"SYNTHETIC TEST ONLY evidence for {key}; no actual decision.\n")
        self.h.bind(self.run, key, str(path), "evidence")
        return self.run["artifacts"][key]

    def propose_change(self, approved=True):
        control = self.run["component_control"]
        proposal = self.evidence_file("component-proposal")
        baseline = self.run["artifacts"][control["baseline_artifact"]]
        control.update({"decision": "change-required", "proposal_artifact": "component-proposal",
                        "reviews": [], "approval": None})
        for kind in eh.COMPONENT_REVIEW_KINDS:
            key = "review-" + kind
            proof = self.evidence_file(key)
            control["reviews"].append({
                "kind": kind, "actor": "independent-agent" if kind == "independent-feasibility" else self.run["owner"],
                "verdict": "change-justified", "artifact": key, "sha256": proof["sha256"],
                "locator": "TEST ONLY synthetic component review", "proposal_sha256": proposal["sha256"],
                "baseline_sha256": baseline["sha256"],
            })
        if approved:
            proof = self.evidence_file("component-approval", "TEST ONLY fictional user quote; not real permission.\n")
            control["approval"] = {
                "status": "approved", "authority": "user", "artifact": "component-approval",
                "sha256": proof["sha256"], "locator": "TEST ONLY fictional message",
                "message_ref": "TEST-ONLY-USER-MESSAGE-001", "source": "TEST ONLY fictional chat transcript",
                "quote": "TEST ONLY: I approve this exact synthetic proposal.",
                "proposal_sha256": proposal["sha256"], "baseline_sha256": baseline["sha256"],
            }

    def mark(self, check_id, status="PASS", evidence=None):
        self.h.mark(self.run, check_id, "run", status, "TEST ONLY synthetic component observation, not an actual approval",
                    self.run["owner"], "inspection", list(self.run["artifacts"]) if evidence is None else evidence,
                    "TEST ONLY synthetic fixture section")

    def complete_change(self):
        for c, target in self.h.required(self.run, "release"):
            independent = c["id"] == "independent-review"
            self.h.mark(self.run, c["id"], target, "PASS", "TEST ONLY synthetic observation, no actual engineering result",
                        "release-agent" if independent else self.run["owner"],
                        "independent-review" if independent else "inspection", list(self.run["artifacts"]),
                        "TEST ONLY synthetic fixture section")

    def test_new_run_initializes_unknown_control_and_cannot_claim_component_pass(self):
        fresh = self.h.create("new-control-test", ["part"], ["plate"], "other-petg", "prototype")
        self.assertEqual(fresh["component_control"], {
            "decision": "unknown", "register_artifact": None, "baseline_artifact": None,
            "comparison_artifact": None, "proposal_artifact": None, "reviews": [], "approval": None,
        })
        for check_id in eh.COMPONENT_CHECKS:
            with self.subTest(check_id=check_id), self.assertRaises(eh.HarnessError):
                self.mark(check_id)

    def test_unchanged_components_pass_without_user_approval(self):
        self.complete_unchanged()
        self.assertIsNone(self.run["component_control"]["approval"])
        self.assertEqual(self.run["component_control"]["reviews"], [])
        result = self.h.validate(self.run, "intake")
        self.assertTrue(result["passed"], result["errors"])

    def test_simplicity_review_is_required_even_without_component_changes(self):
        self.complete_unchanged()
        self.run["checks"] = [r for r in self.run["checks"] if r["id"] != "assembly-simplicity"]
        self.assertTrue(self.h.validate(self.run, "intake")["passed"])
        for stage in ("design", "slice", "release"):
            result = self.h.validate(self.run, stage)
            self.assertFalse(result["passed"])
            self.assertTrue(any("assembly-simplicity@run: missing check" in e for e in result["errors"]))
        with self.assertRaises(eh.HarnessError):
            self.mark("assembly-simplicity", "N/A")
        self.mark("assembly-simplicity", "FAIL")
        self.assertFalse(self.h.validate(self.run, "design")["passed"])

    def test_each_component_check_is_mandatory_at_intake_and_forbids_na(self):
        self.complete_unchanged()
        original = deepcopy(self.run)
        self.assertTrue(eh.COMPONENT_CHECKS.issubset({c["id"] for c in self.h.catalog}))
        for check_id in eh.COMPONENT_CHECKS:
            with self.subTest(check_id=check_id):
                self.run = deepcopy(original)
                self.run["checks"] = [r for r in self.run["checks"] if r["id"] != check_id]
                result = self.h.validate(self.run, "intake")
                self.assertFalse(result["passed"])
                self.assertTrue(any(f"{check_id}@run: missing check" in e for e in result["errors"]))
                with self.assertRaises(eh.HarnessError):
                    self.mark(check_id, "N/A")

    def test_register_requires_canonical_path_separate_baseline_and_comparison(self):
        control = self.run["component_control"]
        control["decision"] = "unchanged"
        original = deepcopy(self.run)
        for field in ("register_artifact", "baseline_artifact", "comparison_artifact"):
            with self.subTest(missing=field):
                self.run = deepcopy(original)
                self.run["component_control"][field] = None
                with self.assertRaises(eh.HarnessError):
                    self.mark("external-components-baseline")
        self.run = deepcopy(original)
        other = self.root / "noncanonical-register.md"
        other.write_text("TEST ONLY not the canonical assembly inventory")
        self.h.bind(self.run, "components-register", str(other), "component-register")
        with self.assertRaisesRegex(eh.HarnessError, "canonical path"):
            self.mark("external-components-baseline")
        self.run = deepcopy(original)
        self.h.bind(self.run, "components-baseline", eh.COMPONENT_REGISTER, "component-baseline")
        with self.assertRaisesRegex(eh.HarnessError, "separate preserved snapshot"):
            self.mark("external-components-baseline")
        self.run = deepcopy(original)
        self.h.bind(self.run, "components-comparison", "components-baseline.md", "evidence")
        with self.assertRaisesRegex(eh.HarnessError, "separate assessment"):
            self.mark("external-components-baseline")

    def test_baseline_check_must_cite_the_actual_comparison_files(self):
        self.run["component_control"]["decision"] = "unchanged"
        with self.assertRaisesRegex(eh.HarnessError, "must cite all required"):
            self.mark("external-components-baseline", evidence=["proof"])

    def test_unchanged_cannot_hide_a_leftover_proposal_review_or_approval(self):
        self.propose_change()
        original = deepcopy(self.run)
        for field in ("proposal_artifact", "reviews", "approval"):
            with self.subTest(field=field):
                self.run = deepcopy(original)
                control = self.run["component_control"]
                leftovers = control[field]
                control.update({"decision": "unchanged", "proposal_artifact": None,
                                "reviews": [], "approval": None})
                control[field] = leftovers
                with self.assertRaisesRegex(eh.HarnessError, "cannot retain"):
                    self.mark("component-change-necessity")

    def test_change_requires_three_distinct_positive_review_passes(self):
        self.propose_change()
        original = deepcopy(self.run)
        for count in range(3):
            with self.subTest(count=count):
                self.run = deepcopy(original)
                self.run["component_control"]["reviews"] = self.run["component_control"]["reviews"][:count]
                with self.assertRaisesRegex(eh.HarnessError, "three distinct"):
                    self.mark("component-change-necessity")
        self.run = deepcopy(original)
        self.run["component_control"]["reviews"][1]["kind"] = "technical-necessity"
        with self.assertRaisesRegex(eh.HarnessError, "three distinct"):
            self.mark("component-change-necessity")
        self.run = deepcopy(original)
        self.run["component_control"]["reviews"][0]["verdict"] = "preserve-current-components"
        with self.assertRaisesRegex(eh.HarnessError, "positive verdict"):
            self.mark("component-change-necessity")

    def test_independent_necessity_review_cannot_be_owner_or_reused_report(self):
        self.propose_change()
        original = deepcopy(self.run)
        self.run["component_control"]["reviews"][2]["actor"] = self.run["owner"]
        with self.assertRaisesRegex(eh.HarnessError, "differ from run owner"):
            self.mark("component-change-necessity")
        self.run = deepcopy(original)
        reviews = self.run["component_control"]["reviews"]
        reviews[2]["artifact"] = reviews[0]["artifact"]
        reviews[2]["sha256"] = reviews[0]["sha256"]
        with self.assertRaisesRegex(eh.HarnessError, "separate independent review"):
            self.mark("component-change-necessity")

    def test_multiple_reviews_do_not_authorize_component_change(self):
        self.propose_change(approved=False)
        self.mark("component-change-necessity")
        with self.assertRaisesRegex(eh.HarnessError, "explicit user approval"):
            self.mark("component-change-user-approval")
        self.assertFalse(self.h.validate(self.run, "intake")["passed"])

    def test_user_approval_requires_exact_authority_quote_and_message_provenance(self):
        self.propose_change()
        original = deepcopy(self.run)
        for field, bad in (("authority", "reviewer"), ("status", "PASS"), ("quote", ""),
                           ("source", ""), ("message_ref", ""), ("locator", "")):
            with self.subTest(field=field):
                self.run = deepcopy(original)
                self.run["component_control"]["approval"][field] = bad
                with self.assertRaisesRegex(eh.HarnessError, "explicit approved user"):
                    self.mark("component-change-user-approval")

    def test_exact_synthetic_user_approval_after_all_reviews_allows_gate(self):
        self.propose_change()
        self.complete_change()
        result = self.h.validate(self.run, "release")
        self.assertTrue(result["passed"], result["errors"])

    def test_proposal_or_baseline_change_requires_new_reviews_and_user_approval(self):
        for key in ("component-proposal", "components-baseline"):
            with self.subTest(key=key):
                self.setUp()
                self.propose_change()
                self.complete_change()
                artifact = self.run["artifacts"][key]
                path = self.root / artifact["path"]
                path.write_text(path.read_text() + "TEST ONLY revised exact contents\n")
                self.assertFalse(self.h.validate(self.run, "intake")["passed"])
                self.h.bind(self.run, key, str(path), artifact["role"])
                with self.assertRaisesRegex(eh.HarnessError, "current exact proposal and baseline"):
                    self.mark("component-change-necessity")
                control = self.run["component_control"]
                for review in control["reviews"]:
                    review["proposal_sha256"] = self.run["artifacts"]["component-proposal"]["sha256"]
                    review["baseline_sha256"] = self.run["artifacts"]["components-baseline"]["sha256"]
                self.mark("component-change-necessity")
                with self.assertRaisesRegex(eh.HarnessError, "current exact proposal and baseline"):
                    self.mark("component-change-user-approval")

    def test_review_or_approval_evidence_changes_remain_stale_after_rebind(self):
        for key, check_id in (("review-technical-necessity", "component-change-necessity"),
                              ("component-approval", "component-change-user-approval")):
            with self.subTest(key=key):
                self.setUp()
                self.propose_change()
                self.complete_change()
                path = self.root / self.run["artifacts"][key]["path"]
                path.write_text(path.read_text() + "TEST ONLY changed evidence\n")
                self.assertFalse(self.h.validate(self.run, "intake")["passed"])
                self.h.bind(self.run, key, str(path), "evidence")
                with self.assertRaisesRegex(eh.HarnessError, "stale evidence hash"):
                    self.mark(check_id)

    def test_comparison_change_and_rebind_stales_the_previous_component_checks(self):
        self.complete_unchanged()
        path = self.root / "components-comparison.md"
        path.write_text(path.read_text() + "TEST ONLY revised comparison\n")
        self.h.bind(self.run, "components-comparison", str(path), "evidence")
        result = self.h.validate(self.run, "intake")
        self.assertFalse(result["passed"])
        self.assertTrue(any("missing or replaced evidence" in e for e in result["errors"]))

    def test_component_control_changes_invalidate_existing_passes(self):
        self.complete_unchanged()
        old_basis = self.h.basis(self.run, "intake")
        self.run["component_control"]["additional_decision_observation"] = "TEST ONLY changed assessment"
        self.assertNotEqual(old_basis, self.h.basis(self.run, "intake"))
        result = self.h.validate(self.run, "intake")
        self.assertFalse(result["passed"])
        self.assertTrue(any("stale review basis" in e for e in result["errors"]))

    def test_register_update_stales_checks_but_retains_exact_proposal_approval(self):
        self.propose_change()
        self.complete_change()
        approval = deepcopy(self.run["component_control"]["approval"])
        path = self.root / eh.COMPONENT_REGISTER
        path.write_text(path.read_text() + "TEST ONLY updated current inventory after synthetic approval\n")
        self.h.bind(self.run, "components-register", str(path), "component-register")
        self.assertFalse(self.h.validate(self.run, "intake")["passed"])
        self.complete_change()
        self.assertEqual(approval, self.run["component_control"]["approval"])
        result = self.h.validate(self.run, "intake")
        self.assertTrue(result["passed"], result["errors"])

    def test_missing_or_malformed_control_blocks_without_crashing(self):
        original = deepcopy(self.run)
        for value in (None, {}, {**original["component_control"], "decision": []},
                      {**original["component_control"], "reviews": None}):
            with self.subTest(value=value):
                self.run = deepcopy(original)
                self.run["component_control"] = value
                self.assertFalse(self.h.validate(self.run, "intake")["passed"])
        self.run = deepcopy(original)
        del self.run["component_control"]
        self.assertFalse(self.h.validate(self.run, "intake")["passed"])


if __name__ == "__main__":
    unittest.main()
