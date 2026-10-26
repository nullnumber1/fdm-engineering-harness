---
name: print-release-audit
description: Audit final FDM jobs in this repository before delivering them as ready, uploading or printing; require every engineering check, independent review and current hashes for the exact job.
---

# Print release audit

Read the [engineering specification](../../../harness/ENGINEERING-SPEC-RU.md)
and all release checks in [the catalog](../../../harness/checks.json).
Release includes intake, design and slice for every part/plate. Historical
files have no automatic exemption.
Require `purpose: production` for product parts and the finished assembly's full
criteria. Reject a release justified only for cold fit, no tightening, a future
reprint or prototype risk. A pending post-manufacturing inspection is recorded
honestly; it does not excuse a critical design or process unknown before print.
Read the [surface-quality procedure](../../../harness/SUPPORTED-SURFACES-RU.md).
Independently verify manufacturing_quality face/edge/support-group coverage,
engineering acceptance budgets or actual physical evidence and applicability. Inspect
model curl above stable native supports as well as roots and removal. Require
all four quality gates; unknown critical supported/bridge quality cannot be
waived by a trial label. Check that any calibration exception is genuinely a
bounded surface experiment, not a renamed full product part. Synthetic test
fixtures and owner-written PASS are not physical evidence.
Challenge whether a substantial CAD/orientation change improves the product:
check the actual failure mechanism, targeted process/accepted-geometry
alternatives and the resulting function, openings, strength, simplicity and
manufacturing risk. Zero supports, zero bridge roles, 100% infill or a fixed
road count are not product goals. Do not invent a blanket flat/edge rule or
fresh-coupon requirement. A critical unresolved quality issue still blocks.

1. Obtain the run, complete inventory, final files and evidence. Validate slice.
   Read the [component register](../../../harness/ASSEMBLY-COMPONENTS-RU.md).
   Verify the final component/fastener delta against the captured baseline,
   three reviews and exact human approval when components changed. Trial
   or print authorization alone does not approve a component substitution.
   Reconcile actual exported objects and copies with the inventory, independently
   of filenames and author claims. Enforce native-supports-only: confirm that
   CAD/exports contain no custom support parts or fused sacrificial geometry,
   and that supports originate from the native slicer generator. Any such CAD
   aid is FAIL; unclear origin is UNKNOWN for every job.
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
   Validate conservative geometry/seam flags and sufficient risk coverage;
   distinguish a method limitation from a demonstrated product defect. A
   justified actual section may differ from the thin-feature fallback, but
   continuity, forming base, seam safety and genuine thin roots stay covered.
   Reject relabeling a known failed surface or rewriting an old test signature
   as evidence of success. Accepted equivalent feature groups are valid coverage.
3. Resolve findings, rebuild/reslice, rebind and repeat affected checks against
   the product's full requirements. Record actual physical verification and
   pending post-manufacturing acceptance separately. A bounded calibration
   coupon supplies evidence only after a real accepted result; it is not the
   requested product. Preserve historical prototype records without upgrading
   them by renaming or changing purpose alone.
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
