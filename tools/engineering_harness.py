#!/usr/bin/env python3
"""Evidence and file freshness gate for this repository's FDM engineering work.

This validates the review record, not physical strength or print success.
It never imports CAD software, slices, contacts a printer, or starts a job.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any
from zipfile import BadZipFile, ZipFile

STAGES = ("intake", "design", "slice", "release")
STATUSES = ("UNKNOWN", "PASS", "FAIL", "N/A")
ROLES = {
    "source": 0, "measurement": 0, "machine-profile": 0,
    "component-register": 0, "component-baseline": 0,
    "filament-profile": 0, "process-profile": 0, "geometry": 1,
    "project": 2, "gcode": 2, "gcode-baseline": 2, "evidence": None,
}
METHODS = ("scope", "measurement", "inspection", "calculation", "test", "independent-review")
GENERATED_MARKER = "<!-- engineering-harness generated; edit the JSON review record instead -->"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$")
COMPONENT_REGISTER = "harness/ASSEMBLY-COMPONENTS-RU.md"
COMPONENT_CHECKS = {
    "external-components-baseline", "component-change-necessity", "component-change-user-approval",
}
COMPONENT_REVIEW_KINDS = (
    "technical-necessity", "preserve-current-alternatives", "independent-feasibility",
)
POLICY_FILES = (
    "AGENTS.md", "harness/checks.json", "harness/ENGINEERING-SPEC-RU.md",
    "harness/GCODE-MODIFICATION-RU.md",
    ".agents/skills/fdm-design/SKILL.md",
    ".agents/skills/bambu-petg-preparation/SKILL.md",
    ".agents/skills/print-release-audit/SKILL.md",
    "tools/engineering_harness.py",
    "tools/gcode_modal_audit.py",
)


class HarnessError(ValueError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=".engineering-", delete=False) as stream:
        temp = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temp.replace(path)


def text_present(value: Any, minimum: int = 1) -> bool:
    return (isinstance(value, str) and len(value.strip()) >= minimum
            and value.strip().lower() not in {"todo", "tbd", "ok", "pass", "checked", "проверено"})


class Harness:
    def __init__(self, root: Path):
        self.root = root.resolve()
        try:
            catalog = json.loads((self.root / "harness/checks.json").read_text())
        except (OSError, ValueError) as exc:
            raise HarnessError(f"Cannot read check catalog: {exc}") from exc
        if catalog.get("schema_version") != 1 or not isinstance(catalog.get("checks"), list):
            raise HarnessError("Unsupported check catalog")
        self.catalog = catalog["checks"]
        ids = set()
        for c in self.catalog:
            if (not isinstance(c, dict) or not ID_RE.fullmatch(str(c.get("id", "")))
                    or c["id"] in ids or c.get("stage") not in STAGES
                    or c.get("scope") not in {"run", "part", "plate"}
                    or type(c.get("na_allowed")) is not bool
                    or not text_present(c.get("title")) or not text_present(c.get("requirement"))):
                raise HarnessError("Malformed or duplicate check in catalog")
            ids.add(c["id"])
        if not self.catalog or not all(any(c["stage"] == s for c in self.catalog) for s in STAGES):
            raise HarnessError("Catalog must cover every stage")

    def local_path(self, raw: str | Path) -> Path:
        p = Path(raw)
        p = (self.root / p if not p.is_absolute() else p).resolve()
        if not p.is_relative_to(self.root):
            raise HarnessError(f"Path outside repository: {raw}")
        return p

    def policy(self) -> dict[str, str]:
        result = {}
        for name in POLICY_FILES:
            p = self.local_path(name)
            if not p.is_file():
                raise HarnessError(f"Missing harness policy file: {name}")
            result[name] = digest(p)
        return result

    def load(self, name: str | Path) -> dict:
        try:
            value = json.loads(self.review_path(name).read_text())
        except (OSError, ValueError) as exc:
            raise HarnessError(f"Cannot read run: {exc}") from exc
        if not isinstance(value, dict):
            raise HarnessError("Run must be a JSON object")
        return value

    def review_path(self, name: str | Path) -> Path:
        path = self.local_path(name)
        if path.suffix.lower() != ".json" or not path.is_relative_to(self.root / "harness/runs"):
            raise HarnessError("Run JSON must be stored under harness/runs/")
        return path

    def bound_paths(self) -> set[Path]:
        """Protect evidence of every registered run, including from catalog output."""
        protected = set()
        for path in (self.root / "harness/runs").rglob("*.json"):
            try:
                path = self.local_path(path)
                run = json.loads(path.read_text())
                if not isinstance(run, dict) or run.get("schema_version") != 1 or not isinstance(run.get("artifacts"), dict):
                    raise ValueError("not a review record")
                for artifact in run["artifacts"].values():
                    if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
                        raise ValueError("invalid artifact binding")
                    protected.add(self.local_path(artifact["path"]))
            except (OSError, ValueError, TypeError) as exc:
                raise HarnessError(f"Cannot establish output protection for run {path.name}: {exc}") from exc
        return protected

    def write_markdown(self, name: str, content: str, run: dict | None = None,
                       run_path: str | None = None) -> Path:
        path = self.local_path(name)
        if path.suffix.lower() != ".md":
            raise HarnessError("Generated checklists require a .md output path")
        protected = {self.local_path(p) for p in POLICY_FILES}
        protected.update(self.bound_paths())
        if run_path is not None:
            protected.add(self.local_path(run_path))
        if run is not None:
            protected.update(self.local_path(a["path"]) for a in run["artifacts"].values())
        if path in protected:
            raise HarnessError("Generated output cannot overwrite policy, run or bound evidence/artifacts")
        if path.exists() and not path.read_text(encoding="utf-8").startswith(GENERATED_MARKER + "\n"):
            raise HarnessError("Refusing to overwrite a file not generated by this harness")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def required(self, run: dict, stage: str) -> list[tuple[dict, str]]:
        limit = STAGES.index(stage)
        rows = []
        for c in self.catalog:
            if STAGES.index(c["stage"]) > limit:
                continue
            targets = ["run"] if c["scope"] == "run" else [
                f"{c['scope']}:{k}" for k in sorted(run[c["scope"] + "s"])]
            rows.extend((c, target) for target in targets)
        return rows

    def structural_errors(self, run: dict) -> list[str]:
        errors = []
        if run.get("schema_version") != 1:
            errors.append("Unsupported run schema")
        if not text_present(run.get("run_id")) or not text_present(run.get("owner")):
            errors.append("run_id and owner are required")
        if run.get("purpose") not in {"production", "prototype", "calibration"}:
            errors.append("Explicit purpose required: production/prototype/calibration")
        for name in ("artifacts", "parts", "plates"):
            v = run.get(name)
            if not isinstance(v, dict):
                errors.append(f"{name} must be an object")
                continue
            if name != "artifacts" and not v:
                errors.append(f"Explicit nonempty {name} inventory required")
            for key, item in v.items():
                if not ID_RE.fullmatch(key) or not isinstance(item, dict):
                    errors.append(f"Invalid {name} entry: {key}")
        if not isinstance(run.get("checks"), list):
            errors.append("checks must be an array")
        control = run.get("component_control")
        required_control = {"decision", "register_artifact", "baseline_artifact", "comparison_artifact",
                            "proposal_artifact", "reviews", "approval"}
        if not isinstance(control, dict) or not required_control.issubset(control):
            errors.append("Explicit complete component_control object required")
        elif (control["decision"] not in ("unknown", "unchanged", "change-required")
              or not isinstance(control["reviews"], list)
              or (control["approval"] is not None and not isinstance(control["approval"], dict))
              or any(control[k] is not None and not isinstance(control[k], str)
                     for k in ("register_artifact", "baseline_artifact", "comparison_artifact", "proposal_artifact"))):
            errors.append("Invalid component_control fields or decision")
        p = run.get("profile")
        if not isinstance(p, dict):
            errors.append("Explicit manufacturing profile required")
        else:
            if p.get("printer") != "Bambu Lab A1":
                errors.append("This policy covers Bambu Lab A1 only")
            if type(p.get("nozzle_mm")) not in {int, float} or p["nozzle_mm"] <= 0:
                errors.append("Positive nozzle_mm required")
            if not text_present(p.get("plate")):
                errors.append("Explicit physical plate required")
            m = p.get("material")
            if not isinstance(m, dict) or m.get("family") != "PETG":
                errors.append("This policy covers PETG only")
            elif (m.get("variant") not in {"bambu-petg-basic", "other-petg"}
                  or not text_present(m.get("manufacturer")) or not text_present(m.get("product"))):
                errors.append("Exact PETG variant, manufacturer/product or explicit unbranded identity required")
            elif m["variant"] == "bambu-petg-basic" and (
                    m["manufacturer"] != "Bambu Lab" or m["product"] != "Bambu PETG Basic"):
                errors.append("Bambu PETG Basic identity mismatch; use other-petg for another product")
        if errors:
            return errors
        artifacts = run["artifacts"]
        for key, item in artifacts.items():
            if item.get("role") not in ROLES or not isinstance(item.get("path"), str):
                errors.append(f"Artifact {key}: invalid role/path")
                continue
            try:
                path = self.local_path(item["path"])
                if not path.is_file() or digest(path) != item.get("sha256"):
                    errors.append(f"Artifact {key}: missing or changed file; rebind and review affected checks")
            except (OSError, ValueError) as exc:
                errors.append(f"Artifact {key}: {exc}")
        for name in ("parts", "plates"):
            for key, item in run[name].items():
                refs = item.get("artifacts")
                if (not isinstance(refs, list) or not all(isinstance(a, str) and a in artifacts for a in refs)
                        or len(refs) != len(set(refs))):
                    errors.append(f"{name}:{key}: invalid artifact references")
                if name == "plates":
                    members = item.get("parts")
                    if (not isinstance(members, list)
                            or not all(isinstance(a, str) and a in run["parts"] for a in members)
                            or len(members) != len(set(members))):
                        errors.append(f"plate:{key}: invalid part membership")
        return errors

    @staticmethod
    def gcode_payloads(path: Path) -> tuple[tuple[str, str], ...]:
        """Exact program-byte signatures; single raw/packed programs are equivalent.

        Multiple archive members retain their names so swapping plate programs is
        not hidden by a container-only comparison. Every archive member is CRC-read.
        """
        try:
            if path.suffix.lower() == ".gcode":
                if path.stat().st_size == 0:
                    raise HarnessError("Empty G-code program")
                return (("", digest(path)),)
            if path.suffix.lower() != ".3mf":
                raise HarnessError("G-code baseline/final must be .gcode or sliced .3mf")
            with ZipFile(path) as archive:
                members = [info for info in archive.infolist() if info.filename.lower().endswith(".gcode")]
                if not members or any(info.is_dir() or info.file_size == 0 for info in members):
                    raise HarnessError("3MF requires nonempty G-code payloads")
                if len({info.filename for info in members}) != len(members):
                    raise HarnessError("Duplicate G-code archive members are ambiguous")
                if archive.testzip() is not None:
                    raise HarnessError("3MF archive CRC failure")
                signatures = [(info.filename if len(members) > 1 else "",
                               hashlib.sha256(archive.read(info)).hexdigest()) for info in members]
                return tuple(sorted(signatures))
        except Exception as exc:
            raise HarnessError(f"Cannot read exact G-code payloads: {exc}") from exc

    def gcode_errors(self, run: dict, target: str, row: dict) -> list[str]:
        """Require origin/state evidence and run the narrow guard on every final job."""
        errors = []
        plate = run["plates"][target.split(":", 1)[1]]
        review = plate.get("gcode_review")
        fields = {"customization", "expected_e_mode", "scope_artifact", "baseline_artifact"}
        if not isinstance(review, dict) or not fields.issubset(review):
            return ["Explicit complete per-plate gcode_review required"]
        if review["customization"] not in ("none", "modified"):
            errors.append("G-code customization must be established as none or modified; unknown blocks slicing")
        if review["expected_e_mode"] not in ("relative", "absolute"):
            errors.append("G-code expected_e_mode must be relative or absolute, justified by scope and resolved profiles")
        artifacts = run["artifacts"]
        finals = {key: artifacts[key] for key in plate["artifacts"] if artifacts[key]["role"] == "gcode"}
        if not finals:
            errors.append("G-code review requires every attached final job")
        required_evidence = set(finals)

        def evidence(field: str, role: str) -> dict | None:
            ref = review[field]
            item = artifacts.get(ref) if isinstance(ref, str) else None
            if item is None or item.get("role") != role:
                errors.append(f"G-code {field}: bound {role} artifact required")
                return None
            required_evidence.add(ref)
            return item

        scope = evidence("scope_artifact", "evidence")
        baseline = evidence("baseline_artifact", "gcode-baseline")
        final_paths = {self.local_path(item["path"]) for item in finals.values()}
        if baseline is not None and self.local_path(baseline["path"]) in final_paths:
            errors.append("G-code baseline must be a separate immutable native job, not a final job alias")
        if scope is not None and (self.local_path(scope["path"]) in final_paths
                                  or (baseline is not None and self.local_path(scope["path"]) == self.local_path(baseline["path"]))):
            errors.append("G-code scope must be separate origin and before/after review evidence")
        refs = row.get("evidence")
        linked = {ref.get("artifact") for ref in refs if isinstance(ref, dict)
                  and isinstance(ref.get("artifact"), str)} if isinstance(refs, list) else set()
        if required_evidence - linked:
            errors.append("G-code review must cite every final job, scope and native baseline: "
                          + ", ".join(sorted(required_evidence - linked)))

        baseline_programs = None
        if baseline is not None:
            try:
                baseline_programs = self.gcode_payloads(self.local_path(baseline["path"]))
            except HarnessError as exc:
                errors.append(f"G-code baseline: {exc}")
        for key, item in finals.items():
            path = self.local_path(item["path"])
            try:
                programs = self.gcode_payloads(path)
                if (review["customization"] == "none" and baseline_programs is not None
                        and programs != baseline_programs):
                    errors.append(f"G-code {key}: none declaration differs from exact native baseline payloads")
            except HarnessError as exc:
                errors.append(f"G-code {key}: {exc}")

        if review["expected_e_mode"] in ("relative", "absolute"):
            try:
                helper_path = self.local_path("tools/gcode_modal_audit.py")
                module_name = "engineering_gcode_guard_" + digest(helper_path)
                guard = sys.modules.get(module_name)
                if guard is None:
                    spec = importlib.util.spec_from_file_location(module_name, helper_path)
                    if spec is None or spec.loader is None:
                        raise HarnessError("Cannot load G-code modal guard")
                    guard = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = guard
                    try:
                        spec.loader.exec_module(guard)
                    except Exception:
                        sys.modules.pop(module_name, None)
                        raise
                for key, item in finals.items():
                    report = guard.audit_path(self.local_path(item["path"]), review["expected_e_mode"])
                    if not isinstance(report, dict) or report.get("status") != "PASS":
                        status = report.get("status", "UNKNOWN") if isinstance(report, dict) else "UNKNOWN"
                        errors.append(f"G-code {key}: narrow modal guard {status}; inspect gcode_modal_audit report")
            except Exception as exc:
                errors.append(f"G-code modal guard unavailable or failed: {exc}")
        return errors

    def basis(self, run: dict, stage: str) -> str:
        limit = STAGES.index(stage)
        subject = {key: item for key, item in run["artifacts"].items()
                   if ROLES.get(item["role"]) is not None and ROLES[item["role"]] <= limit}
        parts = {key: (item if limit >= 1 else {}) for key, item in run["parts"].items()}
        plates = {key: (item if limit >= 2 else {"parts": item["parts"]})
                  for key, item in run["plates"].items()}
        return stable_hash({"policy": self.policy(), "run_id": run["run_id"],
                            "purpose": run["purpose"], "owner": run["owner"],
                            "profile": run["profile"], "artifacts": subject,
                            "parts": parts, "plates": plates,
                            "component_control": run["component_control"]})

    def component_errors(self, run: dict, check_id: str, row: dict) -> list[str]:
        """Validate traceable review/approval records, never infer human authorization.

        Evidence content and the claimed user's actual identity must still be checked
        honestly by the agent. File integrity and explicit approval pins are enforced here.
        """
        control = run["component_control"]
        artifacts = run["artifacts"]
        errors: list[str] = []
        required_evidence: set[str] = set()

        def artifact(ref: Any, role: str, label: str) -> dict | None:
            value = artifacts.get(ref) if isinstance(ref, str) else None
            if value is None or value.get("role") != role:
                errors.append(f"{label}: bound {role} artifact required")
                return None
            required_evidence.add(ref)
            return value

        register = artifact(control["register_artifact"], "component-register", "component register")
        baseline = artifact(control["baseline_artifact"], "component-baseline", "component baseline")
        comparison = artifact(control["comparison_artifact"], "evidence", "component comparison")
        if register is not None and self.local_path(register["path"]) != self.local_path(COMPONENT_REGISTER):
            errors.append(f"component register: canonical path {COMPONENT_REGISTER} required")
        if baseline is not None and (self.local_path(baseline["path"]) == self.local_path(COMPONENT_REGISTER)
                                     or (register is not None and baseline["path"] == register["path"])):
            errors.append("component baseline: separate preserved snapshot required")
        if comparison is not None and any(
                a is not None and self.local_path(comparison["path"]) == self.local_path(a["path"])
                for a in (register, baseline)):
            errors.append("component comparison: separate assessment evidence required")

        decision = control["decision"]
        if decision == "unknown":
            errors.append("component decision is unknown; establish the baseline and comparison")
        elif decision == "unchanged":
            if (control["proposal_artifact"] is not None or control["reviews"]
                    or control["approval"] is not None):
                errors.append("unchanged components cannot retain a change proposal, reviews or approval")
        elif decision == "change-required":
            proposal = artifact(control["proposal_artifact"], "evidence", "component change proposal")
            if proposal is not None and any(
                    a is not None and self.local_path(proposal["path"]) == self.local_path(a["path"])
                    for a in (register, baseline, comparison)):
                errors.append("component change proposal: separate exact proposal required")
            if check_id != "external-components-baseline":
                reviews = control["reviews"]
                if (len(reviews) != len(COMPONENT_REVIEW_KINDS)
                        or not all(isinstance(r, dict) for r in reviews)
                        or not all(isinstance(r.get("kind"), str) for r in reviews if isinstance(r, dict))
                        or {r.get("kind") for r in reviews if isinstance(r, dict)} != set(COMPONENT_REVIEW_KINDS)):
                    errors.append("component necessity: exactly three distinct required review passes required")
                review_files = {}
                for review in reviews:
                    if not isinstance(review, dict):
                        errors.append("component necessity: malformed review")
                        continue
                    kind = review.get("kind")
                    if not isinstance(kind, str) or kind not in COMPONENT_REVIEW_KINDS:
                        errors.append("component necessity: invalid review kind")
                        continue
                    proof = artifact(review.get("artifact"), "evidence", f"component review {kind}")
                    if (not text_present(review.get("actor"))
                            or review.get("verdict") != "change-justified"
                            or not text_present(review.get("locator"))):
                        errors.append(f"component review {kind}: actor, positive verdict and locator required")
                    if proof is not None:
                        review_files[kind] = self.local_path(proof["path"])
                        if proof["sha256"] != review.get("sha256"):
                            errors.append(f"component review {kind}: stale evidence hash")
                        if proposal is not None and self.local_path(proof["path"]) == self.local_path(proposal["path"]):
                            errors.append(f"component review {kind}: review must be separate from proposal")
                    if (proposal is None or baseline is None
                            or review.get("proposal_sha256") != proposal["sha256"]
                            or review.get("baseline_sha256") != baseline["sha256"]):
                        errors.append(f"component review {kind}: current exact proposal and baseline hashes required")
                    if kind == "independent-feasibility" and review.get("actor") == run["owner"]:
                        errors.append("component independent feasibility: actual reviewer must differ from run owner")
                independent = review_files.get("independent-feasibility")
                if independent is not None and independent in (
                        review_files.get("technical-necessity"), review_files.get("preserve-current-alternatives")):
                    errors.append("component independent feasibility: separate independent review artifact required")
            if check_id == "component-change-user-approval":
                approval = control["approval"]
                if not isinstance(approval, dict):
                    errors.append("component change: explicit user approval required")
                else:
                    proof = artifact(approval.get("artifact"), "evidence", "component user approval")
                    if (approval.get("status") != "approved" or approval.get("authority") != "user"
                            or not all(text_present(approval.get(k)) for k in ("quote", "source", "message_ref", "locator"))):
                        errors.append("component change: explicit approved user quote, source, message_ref and locator required")
                    if proof is not None and approval.get("sha256") != proof["sha256"]:
                        errors.append("component user approval: stale evidence hash")
                    if (proposal is None or baseline is None
                            or approval.get("proposal_sha256") != proposal["sha256"]
                            or approval.get("baseline_sha256") != baseline["sha256"]):
                        errors.append("component user approval: current exact proposal and baseline hashes required")

        refs = row.get("evidence")
        linked = {ref.get("artifact") for ref in refs if isinstance(ref, dict)
                  and isinstance(ref.get("artifact"), str)} if isinstance(refs, list) else set()
        if required_evidence - linked:
            errors.append("component control: check must cite all required register, baseline, comparison and decision evidence: "
                          + ", ".join(sorted(required_evidence - linked)))
        return errors

    def row_errors(self, run: dict, c: dict, target: str, row: dict | None) -> list[str]:
        label = f"{c['id']}@{target}"
        if row is None:
            return [f"{label}: missing check"]
        errors = []
        status = row.get("status")
        if status not in {"PASS", "N/A"}:
            return [f"{label}: {status or 'missing status'}"]
        if status == "N/A" and not c["na_allowed"]:
            errors.append(f"{label}: N/A forbidden for this check")
        if not text_present(row.get("reason"), 12):
            errors.append(f"{label}: specific reason/observation required")
        if not text_present(row.get("actor")) or row.get("method") not in METHODS:
            errors.append(f"{label}: actor and assessment method required")
        if c["id"] == "independent-review" and (row.get("actor") == run["owner"]
                                                  or row.get("method") != "independent-review"):
            errors.append(f"{label}: reviewer must differ from run owner, with independent-review method")
        if c["id"] in COMPONENT_CHECKS:
            errors.extend(f"{label}: {error}" for error in self.component_errors(run, c["id"], row))
        if c["id"] == "gcode-customization-audit":
            errors.extend(f"{label}: {error}" for error in self.gcode_errors(run, target, row))
        if row.get("basis_sha256") != self.basis(run, c["stage"]):
            errors.append(f"{label}: stale review basis; repeat review against current files/policy")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{label}: file evidence required, including for N/A")
        else:
            for ref in evidence:
                if not isinstance(ref, dict):
                    errors.append(f"{label}: invalid evidence")
                    continue
                a = run["artifacts"].get(ref.get("artifact"))
                if a is None or a.get("sha256") != ref.get("sha256"):
                    errors.append(f"{label}: missing or replaced evidence")
                if not text_present(ref.get("locator")):
                    errors.append(f"{label}: evidence locator required (feature, layer, section, field)")
        return errors

    def validate(self, run: dict, stage: str, artifact: str | None = None) -> dict:
        errors = self.structural_errors(run)
        result = {"passed": False, "stage": stage, "run_id": run.get("run_id"),
                  "errors": errors, "checks_required": 0, "checks_passed": 0,
                  "scope": "Review completeness and current-file integrity; no physical certification"}
        if errors:
            return result
        self.policy()
        by_key = {}
        known = {c["id"]: c for c in self.catalog}
        for row in run["checks"]:
            if not isinstance(row, dict):
                errors.append("Malformed check record")
                continue
            check_id, target = row.get("id"), row.get("target")
            if not isinstance(check_id, str) or not isinstance(target, str):
                errors.append("Missing check id/target")
                continue
            key = (check_id, target)
            c = known.get(check_id)
            valid_targets = (["run"] if c and c["scope"] == "run" else
                             [f"{c['scope']}:{x}" for x in run[c["scope"] + "s"]] if c else [])
            if c is None or target not in valid_targets or row.get("status") not in STATUSES:
                errors.append(f"Unexpected check, target or status: {check_id}@{target}")
            if key in by_key:
                errors.append(f"Duplicate check: {check_id}@{target}")
            by_key[key] = row
        if not any(a["role"] == "source" for a in run["artifacts"].values()):
            errors.append("At least one bound authoritative source/requirements file required")
        if STAGES.index(stage) >= 1:
            for part_id, part in run["parts"].items():
                if not any(run["artifacts"][a]["role"] == "geometry" for a in part["artifacts"]):
                    errors.append(f"part:{part_id}: current exported geometry required")
        if STAGES.index(stage) >= 2:
            for role in ("machine-profile", "filament-profile", "process-profile"):
                if not any(a["role"] == role for a in run["artifacts"].values()):
                    errors.append(f"Bound resolved {role} required")
            covered = set()
            for plate_id, plate in run["plates"].items():
                covered.update(plate["parts"])
                if not plate["parts"]:
                    errors.append(f"plate:{plate_id}: explicit nonempty part membership required")
                roles = {run["artifacts"][a]["role"] for a in plate["artifacts"]}
                if not {"project", "gcode"}.issubset(roles):
                    errors.append(f"plate:{plate_id}: final project and sliced G-code files required")
            if covered != set(run["parts"]):
                errors.append("Every declared part must be assigned to a reviewed plate")
        for c, target in self.required(run, stage):
            result["checks_required"] += 1
            e = self.row_errors(run, c, target, by_key.get((c["id"], target)))
            errors.extend(e)
            result["checks_passed"] += not e
        if artifact is not None:
            if stage != "release":
                errors.append("Exact artifact authorization requires stage release")
            path = self.local_path(artifact)
            matches = {key for key, a in run["artifacts"].items()
                       if a["role"] == "gcode" and self.local_path(a["path"]) == path}
            attached = {a for plate in run["plates"].values() for a in plate["artifacts"]}
            if not matches.intersection(attached):
                errors.append("Requested print file is not a bound sliced artifact of a reviewed plate")
            else:
                errors.extend(self.gcode_container_errors(path))
        result["passed"] = not errors
        return result

    @staticmethod
    def gcode_container_errors(path: Path) -> list[str]:
        try:
            if path.suffix.lower() == ".3mf":
                with ZipFile(path) as archive:
                    names = [n for n in archive.namelist() if n.lower().endswith(".gcode")]
                    if not names or any(archive.getinfo(n).file_size == 0 for n in names):
                        return ["Requested 3MF has no nonempty sliced G-code"]
                    if archive.testzip() is not None:
                        return ["Requested 3MF archive is corrupt"]
            elif path.suffix.lower() != ".gcode" or path.stat().st_size == 0:
                return ["Requested print artifact must be nonempty .gcode or sliced .3mf"]
        except (OSError, BadZipFile, RuntimeError) as exc:
            return [f"Invalid sliced artifact: {exc}"]
        return []

    def create(self, run_id: str, parts: list[str], plates: list[str], material: str,
               purpose: str, owner: str = "main-session", product: str | None = None) -> dict:
        if (not parts or not plates or len(parts) != len(set(parts)) or len(plates) != len(set(plates))
                or not all(ID_RE.fullmatch(x) for x in [run_id, *parts, *plates])):
            raise HarnessError("Explicit unique IDs required for run, parts and plates")
        run = {"schema_version": 1, "run_id": run_id, "created_at": now(), "owner": owner,
               "purpose": purpose,
               "component_control": {"decision": "unknown", "register_artifact": None,
                                     "baseline_artifact": None, "comparison_artifact": None,
                                     "proposal_artifact": None, "reviews": [], "approval": None},
               "profile": {"printer": "Bambu Lab A1", "nozzle_mm": 0.4,
                           "plate": "Textured PEI Plate",
                           "material": {"family": "PETG", "variant": material,
                                        "manufacturer": "Bambu Lab" if material == "bambu-petg-basic" else "unknown",
                                        "product": "Bambu PETG Basic" if material == "bambu-petg-basic"
                                        else product or "PETG (unbranded; identity to verify)"}},
               "artifacts": {}, "parts": {p: {"artifacts": []} for p in parts},
               "plates": {p: {"parts": parts[:] if len(plates) == 1 else [], "artifacts": [],
                               "gcode_review": {"customization": "unknown", "expected_e_mode": None,
                                                "scope_artifact": None, "baseline_artifact": None}}
                          for p in plates}, "checks": []}
        for c, target in self.required(run, "release"):
            run["checks"].append({"id": c["id"], "target": target, "status": "UNKNOWN",
                                  "reason": "", "actor": "", "method": "", "evidence": [],
                                  "basis_sha256": ""})
        return run

    def bind(self, run: dict, artifact_id: str, path: str, role: str,
             part: str | None = None, plate: str | None = None) -> None:
        if not ID_RE.fullmatch(artifact_id) or role not in ROLES:
            raise HarnessError("Invalid artifact id/role")
        p = self.local_path(path)
        if not p.is_file():
            raise HarnessError("Artifact must be an existing regular repository file")
        if part is not None and part not in run["parts"]:
            raise HarnessError("Unknown part")
        if plate is not None and plate not in run["plates"]:
            raise HarnessError("Unknown plate")
        run["artifacts"][artifact_id] = {"path": str(p.relative_to(self.root)),
                                         "role": role, "sha256": digest(p)}
        for collection, key in (("parts", part), ("plates", plate)):
            if key is not None and artifact_id not in run[collection][key]["artifacts"]:
                run[collection][key]["artifacts"].append(artifact_id)

    def mark(self, run: dict, check_id: str, target: str, status: str, reason: str,
             actor: str, method: str, evidence: list[str], locator: str) -> None:
        structural = self.structural_errors(run)
        if structural:
            raise HarnessError("; ".join(structural))
        required = {(c["id"], t): c for c, t in self.required(run, "release")}
        c = required.get((check_id, target))
        if c is None or status not in STATUSES:
            raise HarnessError("Unknown check/target/status; inventory must be explicit")
        if any(a not in run["artifacts"] for a in evidence):
            raise HarnessError("Unknown evidence artifact")
        row = {"id": check_id, "target": target, "status": status, "reason": reason,
               "actor": actor, "method": method, "recorded_at": now(),
               "evidence": [{"artifact": a, "sha256": run["artifacts"][a]["sha256"],
                             "locator": locator} for a in evidence],
               "basis_sha256": self.basis(run, c["stage"])}
        if status in {"PASS", "N/A"}:
            errors = self.row_errors(run, c, target, row)
            if errors:
                raise HarnessError("; ".join(errors))
        run["checks"] = [r for r in run["checks"] if (r.get("id"), r.get("target")) != (check_id, target)]
        run["checks"].append(row)

    def checklist(self, run: dict) -> str:
        structural = self.structural_errors(run)
        if structural:
            raise HarnessError("; ".join(structural))
        rows = {(r["id"], r["target"]): r for r in run["checks"]}
        lines = [GENERATED_MARKER, "", f"# Инженерная проверка {run['run_id']}", "",
                 "JSON записи является источником статусов. Галочки в этом представлении не редактировать.",
                 "Допуск относится к подготовке печати; испытания готовой детали учитываются отдельно.", ""]
        for stage in STAGES:
            result = self.validate(run, stage)
            lines += [f"## {stage} — {'PASS' if result['passed'] else 'BLOCKED'}", ""]
            for c, target in self.required(run, stage):
                if c["stage"] != stage:
                    continue
                row = rows.get((c["id"], target))
                valid = not self.row_errors(run, c, target, row)
                status = row["status"] if row else "MISSING"
                if row and status in {"PASS", "N/A"} and not valid:
                    status += " / STALE OR INVALID"
                lines += [f"- [{'x' if valid else ' '}] **{c['id']} — {target} — {status}**: {c['title']}",
                          f"  {c['requirement']}"]
                if row and row.get("reason"):
                    lines.append(f"  Наблюдение: {row['reason']}")
                for ref in (row or {}).get("evidence", []):
                    a = run["artifacts"].get(ref["artifact"], {})
                    lines.append(f"  Свидетельство: {a.get('path', ref['artifact'])}; {ref.get('locator', '')}")
            if result["errors"]:
                lines += ["", "Блокирующие результаты:", ""] + [f"- {e}" for e in result["errors"]]
            lines.append("")
        return "\n".join(lines) + "\n"

    def catalog_markdown(self) -> str:
        lines = [GENERATED_MARKER, "", "# Обязательный инженерный список проверок", "",
                 "Сгенерировано из harness/checks.json. Для работы создайте запись new;",
                 "каждый пункт part повторяется для каждой детали, plate — для каждого стола.",
                 "Все пункты изначально не проверены. Наличие этого списка не даёт допуска к печати.", ""]
        for stage in STAGES:
            lines += [f"## {stage}", ""]
            for c in self.catalog:
                if c["stage"] == stage:
                    lines += [f"- [ ] **{c['id']}** ({c['scope']}): {c['title']}",
                              f"  {c['requirement']}",
                              f"  N/A: {'только с доказательством неприменимости' if c['na_allowed'] else 'запрещено'}.", ""]
        return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("new", help="Create an unchecked run; never grants permission")
    p.add_argument("--run", required=True)
    p.add_argument("--part", action="append", required=True)
    p.add_argument("--plate", action="append", required=True)
    p.add_argument("--material", choices=("bambu-petg-basic", "other-petg"), required=True)
    p.add_argument("--purpose", choices=("production", "prototype", "calibration"), required=True)
    p.add_argument("--owner", default="main-session")
    p.add_argument("--product")
    p = sub.add_parser("bind", help="Record existing file bytes, invalidating affected reviews")
    p.add_argument("--run", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--role", choices=tuple(ROLES), required=True)
    p.add_argument("--part")
    p.add_argument("--plate")
    p = sub.add_parser("mark", help="Record a performed check, with evidence and actor")
    p.add_argument("--run", required=True)
    p.add_argument("--check", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--status", choices=STATUSES, required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--method", choices=METHODS, required=True)
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--locator", default="")
    p = sub.add_parser("check", help="Fail closed unless all checks through stage are current")
    p.add_argument("--run", required=True)
    p.add_argument("--stage", choices=STAGES, required=True)
    p.add_argument("--artifact", help="Exact final print file to authorize; release only")
    p = sub.add_parser("checklist", help="Generate readable statuses from a run")
    p.add_argument("--run", required=True)
    p.add_argument("--output")
    p = sub.add_parser("catalog", help="Generate the complete unchecked specification checklist")
    p.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        harness = Harness(Path(__file__).resolve().parents[1])
        if args.command == "new":
            path = harness.review_path(args.run)
            if path.exists():
                raise HarnessError("Run already exists; preserve its review history")
            value = harness.create(path.stem, args.part, args.plate, args.material,
                                   args.purpose, args.owner, args.product)
            atomic_json(path, value)
            print(json.dumps({"created": str(path), "all_checks": "UNKNOWN", "print_release": False}))
        elif args.command == "bind":
            run = harness.load(args.run)
            if harness.local_path(args.path) == harness.local_path(args.run):
                raise HarnessError("The review record cannot be its own evidence")
            harness.bind(run, args.id, args.path, args.role, args.part, args.plate)
            atomic_json(harness.local_path(args.run), run)
            print(json.dumps({"bound": args.id, "review_affected_checks_again": True}))
        elif args.command == "mark":
            run = harness.load(args.run)
            harness.mark(run, args.check, args.target, args.status, args.reason,
                         args.actor, args.method, args.evidence, args.locator)
            atomic_json(harness.local_path(args.run), run)
            print(json.dumps({"recorded": args.check, "target": args.target, "status": args.status}))
        elif args.command == "check":
            result = harness.validate(harness.load(args.run), args.stage, args.artifact)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["passed"] else 1
        else:
            run = harness.load(args.run) if args.command == "checklist" else None
            content = harness.checklist(run) if run is not None else harness.catalog_markdown()
            if args.output:
                path = harness.write_markdown(args.output, content, run,
                                               args.run if run is not None else None)
                print(str(path))
            else:
                print(content)
        return 0
    except (HarnessError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
