#!/usr/bin/env python3
"""Offline, bounded extrusion-mode regression guard; never authorizes printing.

After G90/G91 this guard requires a fresh explicit M82/M83, irrespective of
firmware-specific modal behavior. It does not simulate deposition or the printer.
"""

import argparse
import base64
import binascii
import hashlib
import io
import json
import re
from pathlib import Path
import sys
import zipfile


GUARD_VERSION = "2"
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_ISSUES = 12
START = re.compile(r"^\s*;\s*(?:CHANGE_LAYER|LAYER_CHANGE)\s*$", re.I)
END = re.compile(r"^\s*;\s*(?:EXECUTABLE_BLOCK_END|filament end gcode|machine end gcode)\s*$", re.I)
COMMAND = re.compile(r"^([GMT])(\d+(?:\.\d+)?)", re.I)
WORD = re.compile(r"([A-Z])([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.I)
NUMERIC_WORDS = re.compile(r"(?:[A-Z][+-]?(?:\d+(?:\.\d*)?|\.\d+))+", re.I)
LIMITATIONS = [
    "Narrow explicit extrusion-mode invariant, not complete G-code or firmware validation.",
    "Expected E mode must come from the evidenced, resolved profile; --profile hashes a file but does not resolve it.",
    "Startup/shutdown extrusion, position/feedrate/units/tool/origin restoration, macros and physical deposition need separate review.",
    "Positive E words and a PASS do not prove plastic deposition, physical safety or print readiness.",
    "M622/M623 and native M624/M625 object-skip paths are conservatively merged; unsupported syntax and uncertain paths block PASS.",
]


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _status(issues):
    if any(i["status"] == "FAIL" for i in issues):
        return "FAIL"
    return "UNKNOWN" if issues else "PASS"


def _without_comments(line):
    result, depth = [], 0
    for char in line:
        if char == ";" and depth == 0:
            break
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                raise ValueError("unmatched parenthesis comment")
            depth -= 1
        elif depth == 0:
            result.append(char)
    if depth:
        raise ValueError("unclosed parenthesis comment")
    return "".join(result).strip()


def _has_extra_command(rest):
    # Numeric chunks can concatenate command and parameter words (S250G90G1E.2).
    # A vendor flag such as g39_3rd_layer_detect_flag is textual, not such a chunk.
    return any(NUMERIC_WORDS.fullmatch(chunk)
               and any(word.group(1).upper() in "GMT" for word in WORD.finditer(chunk))
               for chunk in rest.split())


def _native_object_mask(rest):
    # BambuStudio v02.06.00.51 GCode.cpp encodeBase64/_encode_label_ids_to_base64
    # emits exactly one canonical Base64 token for a nonzero uint64_t bitset.
    # Recognize that grammar only; arbitrary textual vendor arguments stay UNKNOWN.
    if not re.fullmatch(r"[A-Za-z0-9+/]{11}=", rest):
        return False
    try:
        decoded = base64.b64decode(rest, validate=True)
    except (binascii.Error, ValueError):
        return False
    return (len(decoded) == 8 and any(decoded)
            and base64.b64encode(decoded).decode("ascii") == rest)


def _member(name, data, expected):
    report = {"name": name, "sha256": _sha(data), "status": "UNKNOWN",
              "body_start_line": None, "body_end_line": None,
              "extrusion_motion_count": 0, "positive_e_motion_count": 0,
              "coordinate_mode_switch_count": 0, "issues": []}
    issues = report["issues"]
    lines = []

    def issue(status, code, line, message):
        item = {"status": status, "code": code, "line": line, "message": message}
        if line is not None:
            item["context"] = [{"line": j + 1, "text": lines[j]}
                               for j in range(max(0, line - 4), min(len(lines), line + 3))]
        # Retain the first definite failure even after many uncertain findings.
        if len(issues) < MAX_ISSUES:
            issues.append(item)
        elif status == "FAIL" and not any(i["status"] == "FAIL" for i in issues):
            issues[-1] = item

    try:
        text = data.decode("utf-8-sig")
        if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
            raise ValueError("binary/control bytes in G-code")
        lines = text.splitlines()
    except (UnicodeError, ValueError) as exc:
        issue("UNKNOWN", "nontext-member", None, str(exc))
        return report
    starts = [i for i, line in enumerate(lines) if START.match(line)]
    endings = [i for i, line in enumerate(lines) if END.match(line)]
    if not starts or not any(i > starts[0] for i in endings):
        issue("UNKNOWN", "missing-body-bounds", None,
              "Need a CHANGE_LAYER/LAYER_CHANGE start and a supported explicit body end marker.")
        return report
    begin = starts[0]
    end = next(i for i in endings if i > begin)
    report.update(body_start_line=begin + 1, body_end_line=end + 1)
    if any(i > end for i in starts):
        issue("UNKNOWN", "uncovered-print-body", end + 1, "Layer markers occur after the selected body end.")

    modes = {"unasserted"}
    frames = []
    last_switch = None
    for index, raw in enumerate(lines[:end]):
        inside = index >= begin
        try:
            line = _without_comments(raw)
        except ValueError as exc:
            if inside:
                issue("UNKNOWN", "unsupported-comment", index + 1, str(exc))
            continue
        if not line:
            continue
        if "*" in line:
            if inside:
                issue("UNKNOWN", "unsupported-checksum", index + 1, "Checksum lines are outside this guard's parser contract.")
            modes = {"unasserted"}
            continue
        line = re.sub(r"^N\d+\s*", "", line, flags=re.I)
        match = COMMAND.match(line)
        if not match:
            if inside:
                issue("UNKNOWN", "unsupported-command", index + 1, "Unrecognized or implicit-motion command syntax.")
            continue
        letter, number = match.groups()
        number = str(int(number)) if float(number).is_integer() else number
        command = letter.upper() + number
        rest = line[match.end():].strip()
        if command == "M624":
            if _native_object_mask(rest):
                # Execute path is checked normally; M625 merges its resulting
                # mode with the skipped path's entry mode. No predicate truth
                # or independent-XYZ/E firmware behavior is assumed.
                frames.append(("M624", set(modes)))
            else:
                if inside:
                    issue("UNKNOWN", "unsupported-object-mask", index + 1,
                          "M624 requires one canonical nonzero 8-byte Base64 object mask.")
                modes = {"unknown-control"}
            continue
        if command in ("M623", "M625"):
            opener = "M622" if command == "M623" else "M624"
            if rest or not frames or frames[-1][0] != opener:
                if inside:
                    issue("UNKNOWN", "unbalanced-conditional", index + 1,
                          "%s must be parameter-free and close the matching %s block." % (command, opener))
                modes = {"unknown-control"}
            else:
                modes |= frames.pop()[1]
            continue
        if _has_extra_command(rest):
            if inside:
                issue("UNKNOWN", "multiple-commands", index + 1, "Multiple commands on one line are unsupported.")
            modes = {"unknown-control"}
            continue
        if command != "M1002" and WORD.sub("", rest).strip():
            if inside:
                issue("UNKNOWN", "unsupported-arguments", index + 1, "Only numeric arguments and documented M1002 textual arguments are supported.")
            modes = {"unknown-control"}
            continue
        if command == "M622":
            frames.append(("M622", set(modes)))
            continue
        if command in ("G90", "G91", "M82", "M83") and rest:
            if inside:
                issue("UNKNOWN", "unsupported-mode-command", index + 1, "Mode commands must be standalone, without parameters or a second command.")
            modes = {"unasserted"}
            continue
        if command in ("G90", "G91"):
            modes = {"unasserted"}
            last_switch = index + 1
            if inside:
                report["coordinate_mode_switch_count"] += 1
            continue
        if command in ("M82", "M83"):
            modes = {"absolute" if command == "M82" else "relative"}
            continue
        if command in ("M98", "M99", "M120", "M121"):
            if inside:
                issue("UNKNOWN", "unsupported-state-control", index + 1, "Macro/state-stack semantics require separate validation.")
            modes = {"unknown-control"}
        if command not in ("G0", "G1", "G2", "G3") or not inside:
            continue
        params = list(WORD.finditer(rest))
        residual = WORD.sub("", rest).strip()
        if residual or any(p.group(1).upper() in "GMTN" for p in params):
            issue("UNKNOWN", "unsupported-motion", index + 1, "Motion parameters are not plain numeric words.")
            continue
        ewords = [p.group(2) for p in params if p.group(1).upper() == "E"]
        if len(ewords) > 1:
            issue("UNKNOWN", "duplicate-e-word", index + 1, "Multiple E words in a motion.")
            continue
        if not ewords:
            continue
        report["extrusion_motion_count"] += 1
        report["positive_e_motion_count"] += float(ewords[0]) > 0
        if modes == {expected}:
            continue
        if "unknown-control" in modes:
            issue("UNKNOWN", "unresolved-state-control", index + 1,
                  "Prior unsupported command or macro/state-stack control invalidated extrusion-mode proof.")
        elif len(modes) > 1 or frames:
            issue("UNKNOWN", "conditional-e-mode", index + 1,
                  "Possible E-mode states %s; conditional restoration cannot prove an unconditional mode." % sorted(modes))
        elif modes == {"unasserted"}:
            issue("FAIL", "missing-explicit-e-mode", index + 1,
                  "E motion lacks explicit %s after the last G90/G91 (line %s), or an initial mode assertion."
                  % ("M83" if expected == "relative" else "M82", last_switch))
        else:
            issue("FAIL", "wrong-e-mode", index + 1,
                  "Asserted E mode %s differs from evidenced expected mode %s." % (sorted(modes), expected))
    if frames:
        issue("UNKNOWN", "unbalanced-conditional", end + 1, "Conditional/object-skip block remains open at print-body end.")
    if not report["positive_e_motion_count"]:
        issue("UNKNOWN", "no-printing-e-motion", None, "No positive E-motion word in the bounded body; printing coverage is unestablished.")
    report["status"] = _status(issues)
    return report


def audit_path(path, expected_e_mode, profile=None):
    """Return JSON-serializable evidence. No file writes or printer access."""
    path = Path(path).resolve()
    report = {"guard_version": GUARD_VERSION, "path": str(path), "container_sha256": None,
              "expected_e_mode": expected_e_mode, "profile": None, "status": "UNKNOWN",
              "members": [], "issues": [], "limitations": list(LIMITATIONS)}
    if expected_e_mode not in ("relative", "absolute"):
        report["issues"].append({"status": "UNKNOWN", "code": "invalid-expected-mode", "message": "Expected mode must be relative or absolute."})
        return report
    try:
        if profile is not None:
            profile = Path(profile).resolve()
            report["profile"] = {"path": str(profile), "sha256": _sha(profile.read_bytes())}
        if path.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("Input exceeds bounded audit size limit")
        data = path.read_bytes()
        report["container_sha256"] = _sha(data)
        if path.suffix.lower() == ".gcode":
            if len(data) > MAX_MEMBER_BYTES:
                raise ValueError("G-code exceeds bounded member size limit")
            report["members"].append(_member(path.name, data, expected_e_mode))
        elif path.suffix.lower() == ".3mf":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = [i for i in archive.infolist() if not i.is_dir() and i.filename.lower().endswith(".gcode")]
                if not entries:
                    raise ValueError("Archive has no .gcode members")
                if len({i.filename for i in entries}) != len(entries):
                    raise ValueError("Duplicate G-code member names")
                if sum(i.file_size for i in entries) > MAX_ARCHIVE_BYTES:
                    raise ValueError("Expanded G-code exceeds bounded audit limit")
                for entry in entries:
                    if entry.file_size > MAX_MEMBER_BYTES:
                        raise ValueError("G-code member exceeds bounded audit limit")
                    report["members"].append(_member(entry.filename, archive.read(entry), expected_e_mode))
        else:
            raise ValueError("Supported inputs are text .gcode or a .3mf ZIP containing .gcode members")
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        report["issues"].append({"status": "UNKNOWN", "code": "input-error", "message": str(exc)})
    for member in report["members"]:
        report["issues"].extend(dict(item, member=member["name"]) for item in member["issues"])
    report["status"] = _status(report["issues"]) if report["members"] else "UNKNOWN"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--expected-e-mode", required=True, choices=("relative", "absolute"))
    parser.add_argument("--profile", type=Path, help="Hash an already resolved/evidenced profile; does not infer its mode")
    parser.add_argument("--output", type=Path, help="Write JSON only to a new file; existing files are never overwritten")
    args = parser.parse_args(argv)
    report = audit_path(args.path, args.expected_e_mode, args.profile)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(serialized)
        except OSError as exc:
            parser.error("Cannot create a new output file: %s" % exc)
    else:
        sys.stdout.write(serialized)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
