# Contributing

Use a focused branch and open a pull request against `main`. Describe the
concrete problem and resulting behavior, the evidence and compatibility impact.
Use short imperative commit subjects consistent with the existing history.

## Scope

This repository distributes reusable A1/PETG instructions and offline review
tools. Keep actual CAD, printer profiles, jobs, run records, stock registers,
credentials and private conversations in the adopting project. The supplied
component register remains an unfilled template.

Read `AGENTS.md` and the engineering specification. Harness maintenance and
synthetic tests use the documented maintenance exception; they do not require
inventing an actual engineering run or claiming a printable release.

## Change rules and code together

- Keep check IDs, scope, N/A rules and run compatibility intentional. Explain
  migrations when required evidence or purpose acceptance changes.
- Update the specification, relevant skill and validator together. New accepted
  evidence routes need positive and negative regressions through public APIs.
- Preserve native-only supports, component-change approval, actual independent
  review and exact-job modal G-code protection. Document engineering limits;
  a synthetic fixture is never a physical observation.
- Validate the analyzer's assumptions before changing product requirements.
  Prefer a bounded useful check over a new universal threshold.

## Validation

```sh
python3 -m unittest discover -s tools/tests -p 'test_*.py'
python3 tools/engineering_harness.py catalog --output harness/CHECKLIST-RU.md
git diff --check
```

When the catalog changes, commit its generated checklist. Check local Markdown
links and CLI examples, including that a newly created run fails intake until
real evidence is recorded. Tests must stay offline and use temporary fixtures.
Do not add real printer transports or hardware tests to this suite.

Changes to policy files invalidate existing review bases. State this in the PR;
do not migrate records by merely replacing hashes or marking unknowns PASS.
Confirm the GitHub checks for the exact PR head before requesting merge.
