# ADR-0005: TypeScript error count only goes down

- Status: Accepted
- Date: 2026-10-05
- Accepted: 2026-10-05 (docs-only; CI enforcement is a later PR)
- Deciders: Engineering Lead
- Consulted: none

## Context
`package.json` script `check` is `tsc`. `tsconfig.json` sets `compilerOptions.noEmit` to `true`, so `npm run check` typechecks and emits nothing. The working assumption for a cap was 82. This ADR records the count measured in the repo; wiring the check into CI is a later change.

## Decision
**The TypeScript error count can only go down.** The cap is the measured baseline, not a guessed number.

Measured 2026-10-05 from `origin/main` at `425e90f1`:

- Command: `npm run check` (resolves to `tsc`; `noEmit` comes from `tsconfig.json`).
- Count command: `grep -c 'error TS'` on that output → **82**.
- Process exit code: 2.

The measured count is 82. That matches the working assumption of 82 (difference 0). The cap is 82.

New changes may lower the count. A change that raises it fails the ratchet once the check exists. Enforcement in CI is a later, separate PR. This ADR is docs-only.

## Consequences
- Positive: the baseline is a number from `npm run check`, and the allowed direction is down.
- Negative: until the later CI PR, nothing blocks a regression; the cap has to be edited in this ADR when the count legitimately drops.
- Follow-ups: a separate PR that runs `npm run check` in CI and fails when `grep -c 'error TS'` is greater than the cap in this ADR.

## Kill criteria
If the ratchet check, once it exists, blocks a P0 ship, pause this ADR.

## Out of scope
CI config, fixing the 82 errors, changing `tsconfig.json` or the `check` script.
