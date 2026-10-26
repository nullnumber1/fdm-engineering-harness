---
name: bambu-petg-preparation
description: Prepare or change Bambu Lab A1 PETG slicing, profiles, custom G-code, supports, cooling, orientation and plate placement; require part and plate engineering evidence before completing the slice.
---

# A1 PETG preparation

Read the [engineering specification](../../../harness/ENGINEERING-SPEC-RU.md)
and all slice checks in [the catalog](../../../harness/checks.json).
Prepare the requested part for its full final function with `purpose: production`;
a cold-fit or prototype label never relaxes dimensions, strength or process
acceptance. Follow the specification's final-product section for missing data.
Read the [surface-quality procedure](../../../harness/SUPPORTED-SURFACES-RU.md)
for supported faces, bridges, model-edge curling and thin contours. Populate
manufacturing_quality and pass supported-surface-quality,
native-support-stability and free-edge-continuity on the exact job. Inspect
each root and interface separately from the model edge above it. Qualify
supported/bridge faces against their actual function and tolerance using the
procedure's engineering justification or applicable physical results. Support
formation alone does not require a new coupon. A remaining critical uncertainty
still blocks the product part. A removable support, dense interface or four
commanded layers alone does not prove a sound surface. Justify section adequacy
and keep continuous material, forming bases and safe actual seams throughout.

1. Require design PASS for production slicing. A slice investigating a blocked
   design stays diagnostic and cannot be released.
   Read the [component register](../../../harness/ASSEMBLY-COMPONENTS-RU.md) and
   reconcile the job's interfaces with its accepted baseline and approved changes.
   If preparation reveals a required component/fastener substitution, return to
   the component-control intake checks; keep it a proposal until the documented
   reviews and exact user approval are complete.
2. Establish the actual nozzle, plate, exact filament and slicer version. Resolve
   machine/process/filament inheritance and object/height modifiers. Bind resolved
   profiles and preserve calibration for that exact material. Keep PETG Basic
   separate from HF and other PETG.
3. Apply the catalog to every part and plate. Require native-supports-only PASS
   for every model. Generate supports only with the slicer's built-in system on
   the finished model; use native painting/enforcers/blockers and brim/raft
   settings. Never create/import custom support meshes or CAD adhesion parts,
   including a custom mesh assigned to print as support. Return existing CAD
   supports for correction and re-export. Inspect native support sections and
   demonstrate removal; tree or from-build-plate-only is not proof of access.
4. Review actual wall paths at loaded roots, bridge anchors and directions,
   ordinary/bridge/overhang/first-layer cooling, layer time, speed, volumetric
   limit and distinct flow settings. Support every changed value with evidence;
   never invent universal PETG numbers.
   Diagnose the mechanism before a substantial CAD correction. Compare local
   interface/gap, bridge flow/width/direction, overlap, modifier boundaries,
   seams, cooling and speed with reasonable orientations of accepted geometry.
   Preserve applicable global flow calibration; more fan, slower printing and
   100% infill are not automatic improvements. Record the hypothesis, actual
   effective delta, result and acceptance margin. Validate suspicious parser
   flags against real joint/line geometry and the method's uncertainty.
5. Inspect the entire plate through height, including after short parts finish.
   Evaluate tall narrow parts and actual first-layer brim/contact paths. Skirt
   does not replace adhesion. Mixed heights need process compatibility review,
   not an automatic ban. For by-object check head/gantry clearance and sequence.
   Compare relevant flat/edge candidates by total quality, rigidity, adhesion,
   nozzle clearance, time and material. A rigid-body tipping calculation alone
   does not prove adhesion or vibration safety. Show a consequential tall or
   changed-shape choice early; no extra universal approval gate is added.
6. Slice and inspect critical layers; export the exact project and sliced job.
   Bind exports to parts/plates. Reconcile actual objects, copies, coordinates
   and transforms with the declared inventory.
   For custom profile/project macros, temperature/layer changes, postprocessing
   or packaging, read [the G-code procedure](../../../harness/GCODE-MODIFICATION-RU.md).
   Preserve a clean baseline and audit every expanded block/branch and its
   downstream XYZ/E/F state. After the last G90/G91 explicitly restore expected
   M83/M82 before E motion; conditional M83 or Preview alone is insufficient.
   Complete gcode-customization-audit for every plate, including evidence of
   unmodified origins when declaring none, and run the bounded modal guard on
   the exact final file. Its PASS does not replace the complete state audit.
7. Record evidence, then run
   `python3 tools/engineering_harness.py check --run harness/runs/NAME.json --stage slice`.
   After edits repeat affected checks. Pass the same run and files to independent
   release review.

Use [existing auditors](../../../harness/EXISTING-CHECKS-RU.md) within their
limits. Successful slicing does not prove strength, support removal, fit or
adhesion. Use equivalent feature groups where justified; do not create an
exhaustive new auditor when a bounded verified method closes the actual risk.
Continue authorized diagnosis while blocked and finish when the stated criteria
pass, rather than continually adding optimization targets.
