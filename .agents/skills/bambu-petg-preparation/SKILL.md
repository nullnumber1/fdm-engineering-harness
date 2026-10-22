---
name: bambu-petg-preparation
description: Prepare or change Bambu Lab A1 PETG slicing, profiles, custom G-code, supports, cooling, orientation and plate placement; require part and plate engineering evidence before completing the slice.
---

# A1 PETG preparation

Read the [engineering specification](../../../harness/ENGINEERING-SPEC-RU.md)
and all slice checks in [the catalog](../../../harness/checks.json).

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
5. Inspect the entire plate through height, including after short parts finish.
   Evaluate tall narrow parts and actual first-layer brim/contact paths. Skirt
   does not replace adhesion. Mixed heights need process compatibility review,
   not an automatic ban. For by-object check head/gantry clearance and sequence.
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
adhesion.
