# ADR 0003: Explicit evidence model

- Status: Accepted
- Date: 2026-11-05

## Context

Reconciliation confirms that an Intention node has a canonical source symbol.
That says where the node is implemented, not that its acceptance criteria hold.
Every Intent IR criterion already names its required evidence (ADR 0002), but
nothing graded that evidence, so "confirmed" was the only notion of done.

## Decision

Each required evidence reference is graded on one ordered scale:

| Level | Meaning | Source |
| --- | --- | --- |
| `declared` | The criterion exists in approved or proposed intent | Derived |
| `mapped` | The node's canonical GUID is confirmed in Reality | Derived |
| `structural` | The named artifact exists as described | Ledger record |
| `tested` | A test exercises the criterion | Ledger record |
| `behaviorally_verified` | A run, demo or QA result observed the behavior | Ledger record |
| `approved` | A person accepted the evidence | Ledger record with `approved_by` |

A reference's kind, the text before its first colon, sets the level it must
reach: `reconciliation` needs `mapped`, `test` needs `tested`, `ci`, `demo`,
`fixture` and `qa` need `behaviorally_verified`, `approval` and `review` need
`approved`, and every other kind needs `structural`. A
`reconciliation:intent:<id>` reference naming the node itself is satisfied by
its confirmed mapping. Any other reconciliation reference needs a record.

Recorded levels live in the committed ledger `.aio-agentic-sdlc/evidence.json`
(schema version 1). Each record binds one exact intent GUID, criterion ID and
required reference to a level, a locator and a summary, with the recording
actor and a timezone-aware time. Derived levels cannot be recorded.
`dag-tool evidence record` is the only write surface: it locks, refuses a
record for a criterion or reference that does not exist, refuses an exact
duplicate, checks that a path locator exists, and atomically replaces the
ledger.

A criterion is satisfied when the node is mapped and each of its references
reaches its required level. A node is complete when every criterion is
satisfied. A record whose path locator no longer exists does not count.
A record whose criterion or reference was edited away is reported as
orphaned, not silently applied.

`dag-tool reconcile --evidence` and `reconcile_dags(include_acceptance=True)`
add this grading to each intent record, citing the supporting records and
listing unverified criteria. Grading never changes a reconciliation
classification and never edits intent.

## Consequences

- "Confirmed" and "complete" are now different claims, and reports say which.
- References start as durable strings, as the Explicit Evidence Model intent
  assumed. Typed adapters that observe evidence directly (a test run, a QA
  ledger entry) can later write records through the same surface.
- Legacy criteria whose only reference is the node's own reconciliation
  reference become complete as soon as they are mapped. That is the honest
  reading of what they require; sharper criteria are ROADMAP M1 work.
- Keeping incomplete nodes in the diff and gating `apply` on evidence are
  follow-ups that consume this grading (ROADMAP M3).
- Amended 2026-11-11 for Seam B (`doc/authority-model.md`). The ledger also
  holds `qa_dispositions`. An approved `revert-node` QA finding reopens one
  criterion: records made before it stop counting for that criterion, the
  node's own reconciliation reference included, until records made after it
  meet each reference again. Grading still never edits intent.
