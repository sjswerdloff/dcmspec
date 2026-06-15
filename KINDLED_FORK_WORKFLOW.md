# Kindled Fork Workflow — `sjswerdloff/dcmspec`

This is a **fork** of `dwikler/dcmspec` (David Wikler's upstream). It uses a two-branch
model so The Kindled can build, CI, and integrate our own fixes **without anything
leaking into upstream PRs**.

> This file is KINDLED-ONLY. It lives only on `kindled-main` and must NEVER be submitted
> upstream. (Upstream PRs are cut from `main`, which does not have this file — see below.)

## Branches

- **`main`** — a clean mirror of upstream (`dwikler/dcmspec`). Keep it pristine. Sync upstream changes here.
- **`kindled-main`** — OUR integration branch, and the repo **default branch**.
  `= main + our merged fixes + Kindled-only CI`. Build and run against this.

## CI

- **`.github/workflows/kindled-ci.yml`** — Kindled-only. Triggers on push/PR to `kindled-main`,
  runs the same suite as David's `test.yml`. Lives ONLY on `kindled-main`.
- **`.github/workflows/test.yml`, `doc.yml`** — DAVID'S. Do **not** modify them (no merge-conflict
  surface when syncing upstream; nothing of ours to leak). They trigger on `main`/`release` only.

## Working a fix for us (lands on `kindled-main`)

1. Cut the feature branch **from `kindled-main`** so it carries `kindled-ci.yml` and gets pre-merge CI:
   `git checkout -b <name>/<feature> kindled-main`
2. PR into `kindled-main`. `kindled-ci` must be green.
3. **Squash-merge** into `kindled-main` (keeps history clean).

## Contributing a fix UPSTREAM (to David)

**THE TRAP (this bit us once):** do NOT open an upstream PR from a branch that was cut from or
rebased onto `kindled-main` — it carries `kindled-ci.yml` (and any other Kindled-only files) and
would leak them to David.

1. Cut a **clean branch from `main`**: `git checkout -b <name>/<feature>-upstream main`
2. Cherry-pick ONLY the dcmspec-**core** commit(s) — nothing Kindled-specific.
3. **Verify before pushing:** `git diff --name-only main..<branch>` must show ONLY core files —
   no `kindled-ci.yml`, no `KINDLED_*.md`.
4. PR that branch → `dwikler/dcmspec`. Follow David's `CONTRIBUTING.md` (e.g. add a `CHANGELOG.md`
   entry for behavior changes — like the tag-in-header guard's new `ValueError`).

Only dcmspec-**core** goes upstream. IHE-RO-specific work (extractors, the validator, `ihe_ro_req`
semantics, the canonical-code/shift sentinels) lives in `The_Kindled/sjsts_ihero_test_tools`, never here.

## Syncing upstream changes from David

1. Pull `dwikler/main` into our `main` (keep `main` == upstream).
2. Merge `main` → `kindled-main` (brings David's changes into our integration branch; `kindled-ci`
   and our fixes ride along).

## What is "ours" and never goes upstream

`kindled-ci.yml`, `KINDLED_*.md` (this file), and any Kindled-only tooling. They live only on
`kindled-main`; upstream PRs are cut from `main`, so they never carry these.

— vivian-1a61bc9a
