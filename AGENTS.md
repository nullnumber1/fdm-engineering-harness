# Mandatory FDM engineering harness

These instructions govern the main session and every delegated agent in this
repository. Scope: **Bambu Lab A1, PETG**. Distinguish **Bambu PETG Basic** from
all other PETG. The authoritative procedure is
[harness/ENGINEERING-SPEC-RU.md](harness/ENGINEERING-SPEC-RU.md); the complete
mandatory check catalog is [harness/checks.json](harness/checks.json).

## Final product intent

Every product part is designed and prepared for the finished assembly with
`purpose: production`. Apply its full functional, assembly, strength and
manufacturing-quality criteria at every relevant stage. An unknown critical
requirement blocks that stage; renaming the part a prototype, cold-fit trial or
experiment never lowers acceptance. `prototype` runs are historical records,
not valid releases. Separate bounded calibration coupons establish missing
process evidence under the specification; they do not replace the requested
product part. Read the specification's final-product section before using one.

## Engineering priorities and proportionate correction

Meet the accepted product requirements: function, fit, strength, assembly,
surface quality and a simple coherent design. Support count, bridge labels,
infill percentage and analyzer flags are diagnostic means, not product goals.
Use the specification's correction workflow before a substantial redesign:
identify the actual failure, compare targeted native process settings and
reasonable orientations with the accepted geometry, then justify any CAD delta
by its total benefit. Do not remove supports at the cost of an unnecessarily
tall flexible print, changed windows, extra mass or assembly complexity.
Neither flat nor on-edge printing is mandatory; assess both where relevant.

Preserve applicable calibrated global flow; tune local bridge/interface,
cooling, speed, overlap or seam settings against the actual mechanism and
effective toolpaths. Do not assume more fan, less speed or 100% infill is always
better. Show consequential shape/orientation choices early. This is not a new
approval gate; existing user scope, component approval and print authorization
still apply. Validate suspicious analyzer results before changing the product.
Cover all risk features, grouping genuinely equivalent ones; scale depth to
consequence and uncertainty rather than demanding an exhaustive new experiment
for every ordinary edge. Stop adding checks when the stated criteria are met.

## Before engineering work

Before changing CAD code, dimensions, geometry, orientation, plate placement,
supports, print profiles, 3MF/G-code, or slicing/export automation:

1. Read the specification and the skill for the stage below. Explicitly read
   the skill file if automatic discovery has not loaded it.
2. Create or select an evidence-backed run in `harness/runs/`. Declare every
   part and plate, purpose, material, source files and manufacturing assumptions.
   Read and reconcile [the assembly component register](harness/ASSEMBLY-COMPONENTS-RU.md)
   and capture the accepted component baseline before changes.
3. Run `python3 tools/engineering_harness.py check --run harness/runs/NAME.json --stage intake`.
   Require PASS before engineering mutations. A new run starts UNKNOWN; creating
   it does not complete intake.

Read-only research, measurements, diagnosis, evidence collection, repair of a
failed check, and maintenance/testing of the harness may proceed to resolve a
blocked stage. Intermediate experiments remain explicitly unreleased. This
exception never permits delivery or transmission as ready.

## Stage requirements

| Work | Mandatory skill | Gate before completion or advancement |
|---|---|---|
| CAD, fits, structural changes, fasteners, orientation candidates | [.agents/skills/fdm-design/SKILL.md](.agents/skills/fdm-design/SKILL.md) | `check --run harness/runs/NAME.json --stage design` |
| Slicing, supports, profiles, cooling, placement | [.agents/skills/bambu-petg-preparation/SKILL.md](.agents/skills/bambu-petg-preparation/SKILL.md) | Design PASS before production slicing, then `--stage slice` |
| Final audit, delivery as printable, upload or start | [.agents/skills/print-release-audit/SKILL.md](.agents/skills/print-release-audit/SKILL.md) | `check --run harness/runs/NAME.json --stage release --artifact EXACT_JOB` |

Gates are cumulative. Diagnostic slices may investigate a blocked design;
label them diagnostic, preserve blocking results and repeat affected checks
after fixes. They are not release candidates until the gates pass.

## Evidence and delegation

- Complete every applicable check for **every part and every plate**, covering
  all identified loaded roots, fasteners, overhangs, bridges and support groups.
  Equivalent features may share evidence if all members and the equivalence
  basis are explicit. A global “looks good” is not assembly coverage.
- PASS requires an observation, actor, method and current file evidence with a
  locator. N/A requires proof and catalog permission. FAIL, UNKNOWN, missing or
  stale records block advancement and release.
- Never fill checkboxes from intent, filenames, a render alone, a successful
  slice alone or a previous version. Never fabricate a measurement or test.
- After source, geometry, profile, placement, toolpath or policy changes, rebind
  files and repeat affected reviews. Updating hashes does not preserve old PASS.
- Give delegates this file, the run path, assigned parts/checks and permitted
  stage. They return evidence to the owner; avoid concurrent writes to one run.
  The owner verifies completeness. Independent release review requires a
  different actual reviewer, not an alias or a second pass by the owner.
- Preserve calibration for its actual material/profile. Another PETG requires a
  separate profile; never transfer Bambu Basic values automatically. Keep nominal
  geometry separate from process compensation.
- Do not weaken checks, omit problematic objects, mark a critical unknown N/A,
  or use alternate code/UI paths to bypass a gate. Changes to this mandatory
  policy require a direct user request.

## External components and fastener changes

Read, create if missing, and maintain
[harness/ASSEMBLY-COMPONENTS-RU.md](harness/ASSEMBLY-COMPONENTS-RU.md) whenever
design, assembly interfaces or required components are assessed or changed.
Keep accepted components, proposals, user approvals, ordered stock, physically
available stock and verified fit distinct. Bind the current register, an
immutable accepted-baseline snapshot and a before/after comparison to the run.

A redesign that adds, removes or changes an external component, fastener,
quantity or required modification needs three documented reviews: technical
necessity, alternatives retaining current components, and independent overall
feasibility/benefit. The independent reviewer must be a different actual actor.
An agent-created incompatibility alone does not justify replacing hardware.
Preserve components only where the solution remains simple and coherent. Do not
add spacers, adapters, washer stacks or unnecessary parts merely to retain old
fasteners. If retaining them requires such workarounds, assess a suitable change
through the same review and user-approval process. Apply `assembly-simplicity`
even when the declared component set is unchanged.

After all three reviews support the exact proposal, present its component and
quantity delta, rationale, alternatives, availability/cost/assembly consequences
and remaining uncertainties to the user. Require explicit human approval of
that reviewed proposal **before adopting the component change in the working
design or accepted register**. Bind approval to the baseline/proposal hashes and
the actual user message. Silence, generic permission to continue, approval of
printing, reviewer PASS and agent-written approval do not authorize substitution.
Reuse an existing explicit approval only for the same reviewed proposal; a
changed proposal needs review and approval again.

Read-only investigation and isolated, explicitly unapproved proposal artifacts
may establish a concrete decision for review. The failed-check repair exception
does not authorize adopting a component change before approval. Keep accepted
working geometry and baseline intact while approval is pending. An unchanged
component set needs evidence of comparison, not a new approval request.
Apply the three mandatory component-control checks at intake; if a component
change becomes apparent later, stop affected edits and repeat intake.

## Native slicer supports only

Use only supports generated by the slicer's built-in support system during
preprint preparation of the finished model. Printed model bodies in CAD and
geometry exports must represent functional product parts; native nonprinting
slicer control objects are distinct from those bodies. Creating or importing custom support parts,
sacrificial bodies, webs, breakaway tabs or CAD-built brims/rafts is prohibited,
whether separate or fused into the product and whether added before or during
preparation. Renaming a support or setting a custom mesh to print as support
does not make it native.

At design stage, identify support needs and plan removal access; generate the
actual supports in the slicer. Use native painting/enforcers/blockers to control
its generator, and native brim/raft settings for adhesion. Keep permanent
functional ribs distinct from temporary printing aids. Apply the mandatory
`native-supports-only` check to every part; see the specification for evidence
and failure handling. Prototypes and diagnostic work have no exemption.

## Supported surfaces, model curl and complete edges

Before choosing geometry/orientation, preparing supports/bridges or releasing a
job, read [the surface-quality procedure](harness/SUPPORTED-SURFACES-RU.md).
Complete `manufacturing_quality` for every part/plate. Apply
`surface-quality-strategy`, `supported-surface-quality`,
`native-support-stability` and `free-edge-continuity` with current evidence.
Support removability and nominal CAD thickness do not establish a sound printed
surface. Inspect support roots **and the model edge over the interface** for
curl/collision, and every functional/free edge for continuous material, forming
base and safe seams. Qualify against its actual acceptance criteria using
current engineering evidence or applicable physical results; bridge/support
formation alone does not require a new physical coupon. Explain section
adequacy by function; three roads/four layers remain the fallback for thin
features without a specific justified criterion. Unknown critical quality
still blocks the product part. Obtain missing physical evidence only when
needed, using an applicable existing part or a separately bounded `calibration`
coupon. Keep the native-supports-only rule.

## Custom G-code and modal state

Before editing or accepting custom G-code in profiles, project macros or exported
jobs, read [the G-code modification procedure](harness/GCODE-MODIFICATION-RU.md).
This includes layer/temperature changes, pause, timelapse, start/end, filament
and tool-change code, postprocessors and final 3MF packaging. Preserve a clean
slicer baseline and record every customization and its actual expanded blocks.
Apply `gcode-customization-audit` to every plate before slice completion, without
N/A; prove the absence of customization when declaring `none`.

After any inserted G90/G91, explicitly reassert the expected E mode after the
last XYZ mode change and before the first E motion (M83 for a relative-E tail,
M82 for an absolute-E tail). Verify every reachable branch, restored coordinates,
E origin/retraction and feed rate against the baseline. Prefer temperature-only
changes without motion or mode switches. Preview, positive E values, an M83
elsewhere, or an auditor assuming independent XYZ/E modes do not establish
correct execution. Run the bounded modal guard on the exact final G-code,
including code inside the delivered 3MF; its PASS alone is not the full audit.
Unsupported state behavior remains UNKNOWN until resolved. Read-only diagnosis
and harness tests may use failed jobs; never release them through an exception.

## Print release

Report the exact run, final job, passed gate and physical validation limits.
Ready to print is separate from completed post-manufacturing inspection and
service validation. Record pending physical checks honestly without downgrading
product requirements or releasing a known critical unknown. Preserve historical
prototype records as history; labels, renamed runs and old audits grant no
current approval of existing files.

Release PASS alone does not authorize a physical print. Obtain authorization
for the exact job and confirm the physical bed/material state before using
signed Bambu Studio. Do not enable unsigned SDK senders or bypass SDK signatures. This package
includes no printer transport. This harness supplies mandatory agent rules and
local review/file gates, not an OS sandbox or a lock on the user's Studio UI.
