# 1. Record architecture decisions

- **Date:** 2026-08-30
- **Status:** Accepted

## Context

STEM-E is a multi year build with several subsystems that will be developed months
apart. Decisions made early (middleware, simulator, where control loops run) are cheap
to make and expensive to reverse, and the reasoning behind them is exactly what gets
lost first.

## Decision

Record every architecturally significant decision as a short numbered file in
`docs/adr/`. A decision is architecturally significant if reversing it would require
changing more than one package, or if a future contributor could reasonably assume the
opposite.

Each record states the context, the decision, and the consequences including the ones we
dislike. Records are immutable once accepted; a change of mind becomes a new record that
supersedes the old one.

## Consequences

- Answering "why is it done this way" costs a file read instead of an excavation.
- `CLAUDE.md` lists the invariants that follow from these records, so the rules and the
  reasoning stay linked.
- Superseded records stay in the repository. The history of a decision is part of it.
