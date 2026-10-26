# Changelog

Changes are grouped by publication date. No versioned release is declared yet.

## Unreleased

### Changed

- Prioritize final product function, fit, strength, surface quality and assembly simplicity. Compare targeted native process settings and reasonable orientations before a substantial CAD redesign.
- Require `purpose: production` for product parts. Preserve historical `prototype` records for diagnosis; renaming them does not grant release.
- Add four manufacturing-quality checks to the previously published catalog: surface strategy, supported-surface quality, native-support stability and free-edge continuity. The catalog now has 48 checks.
- Accept evidence-backed engineering qualification of supported surfaces alongside applicable physical results. Preserve actual test provenance and block unresolved critical quality.
- Allow purpose-specific section justification while retaining continuity, forming-base and seam checks, explicit accepted minima and coverage of genuine thin features.
- Remove the historical flow-ratio number as a prescribed profile; preserve calibration applicable to the actual material and process.

### Added

- `SUPPORTED-SURFACES-RU.md`, structured quality/purpose regressions, engineering rationale and migration instructions.
- Contributor and pull-request guidance; CI covers Python 3.9, 3.11 and 3.13 with pinned action revisions.

### Compatibility

- Run schema stays at `1`, but new mandatory observations and policy hashes invalidate old approval assumptions. See the README migration section.
- This package contains no printer transport, production jobs, private measurements or assembly stock records.

## Initial publication — 2026-10-22

- Published the 44-check catalog, three agent skills, component-change control and modal G-code audit with offline tests.
