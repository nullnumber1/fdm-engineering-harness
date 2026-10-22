---
name: print-release-audit
description: Audit final FDM jobs in this repository before delivering them as ready, uploading or printing; require every engineering check, independent review and current hashes for the exact job.
---

# Print release audit

Read the [engineering specification](../../../harness/ENGINEERING-SPEC-RU.md)
and all release checks in [the catalog](../../../harness/checks.json).
Release includes intake, design and slice for every part/plate. Historical
files have no automatic exemption.

1. Obtain the run, complete inventory, final files and evidence. Validate slice.
   Read the [component register](../../../harness/ASSEMBLY-COMPONENTS-RU.md).
   Verify the final component/fastener delta against the captured baseline,
   three reviews and exact human approval when components changed. Prototype
   or print authorization alone does not approve a component substitution.
   Reconcile actual exported objects and copies with the inventory, independently
   of filenames and author claims. Enforce native-supports-only: confirm that
   CAD/exports contain no custom support parts or fused sacrificial geometry,
   and that supports originate from the native slicer generator. Any such CAD
   aid is FAIL; unclear origin is UNKNOWN, including for prototype jobs.
2. Use a different actual reviewer. Give them the specification, run and raw
   artifacts. They assess loaded roots, support extraction, overhangs/bridges,
   plate stability and effective settings; record identity and evidence. A new
   alias or second owner pass is not independent review.
   Inspect [custom G-code](../../../harness/GCODE-MODIFICATION-RU.md) provenance
   and gcode-customization-audit for every plate. Include profile macros as well
   as postprocessing. Verify restoration after each inserted G90/G91, all
   reachable branches, downstream XYZ/E/F and exact packed G-code. Challenge
   parser/firmware assumptions: Preview and a bounded guard PASS alone do not
   establish correct execution. Unresolved semantics block release.
3. Resolve findings, rebuild/reslice, rebind and repeat affected checks. Keep
   untested fit/strength/resource explicitly untested. Distinguish prototype or
   calibration print release from production qualification.
4. Record all applicable release checks with evidence. Generate the checklist:
   `python3 tools/engineering_harness.py checklist --run harness/runs/NAME.json --output harness/runs/NAME-checklist.md`.
5. Immediately before handoff or an authorized print action run
   `python3 tools/engineering_harness.py check --run harness/runs/NAME.json --stage release --artifact EXACT_JOB`.
   Require exit 0 for the exact file. Report run, file, scope and physical limits.
   Any edit requires affected reviews again.

FAIL, UNKNOWN, missing, stale and unjustified N/A block release. The validator
checks review completeness and file integrity; reviewers perform the engineering
assessments. PASS is not print authorization: follow exact-job and physical
bed/material confirmation rules. This package includes no printer transport;
do not enable unsigned SDK senders or bypass SDK signatures.
