# ADR-0004: Living tech debt register

- Status: Accepted (Engineering Lead decides alone; docs-only)
- Date: 2026-10-05
- Accepted: 2026-10-05
- Deciders: Engineering Lead
- Consulted: none

## Context
Debt already sits in the tree: a large startup migration file (ADR-0002), background loops inside the web lifespan (ADR-0003), two schema systems (ADR-0001), and a stale package name. Those items are easy to lose across PRs. A decision that is docs-only can make the list visible without a runtime change.

## Decision
**Keep a living register at `docs/adr/tech-debt.md`.** Any PR that knowingly adds debt (a skipped test, a TODO hack, a duplicate code path, a type suppression) links a register row in its body. Each row has: id, area/path, what the debt is, why it was taken, owner role, cost if left alone, and an exit condition. Engineering Lead reviews the register weekly at the Monday council.

## Consequences
- Positive: new debt has an owner, a cost, and an exit before it merges; the Monday council has one file to read.
- Negative: authors of debt-adding PRs edit the register in the same PR; a stale register hides the debt it was meant to show.
- Follow-ups: seed only rows verified in the repo; review the file at each Monday council.

## Kill criteria
If the register has no updates for 2 consecutive weeks while debt-adding PRs merge, retire this ADR.

## Out of scope
Paying down seeded rows in this change; CI checks that the PR body links a row; runtime code.
