# Acceptance evidence for eight confirmed nodes, 2026-11-08

Triage authorized eight `acceptance_evidence_required` items: approved
nodes confirmed in Reality whose acceptance criteria had no recorded
evidence (ADR 0003). This change records that evidence. It approves
nothing: no reference in these eight nodes needs `approved` evidence.

| Node | Criteria |
| --- | --- |
| Intent IR v1 | 2 |
| Evidence-Gated Reconciliation Baseline | 3 |
| Approval-Gated Source Mapping | 4 |
| Legacy Intent IR Migration | 4 |
| DAG Visualization and Comparison | 4 |
| MCP SDK v2 Integration | 6 |
| Explicit Source Identity Maintenance | 5 |
| Intention DAG Consistency Check | 2 |

`evidence-plan.json` lists all 82 references. Each one names the
level it needs, every test or artifact that supports it, and a summary.
The ledger keeps one record per reference, so a record's locator is the
first entry and its summary names the others.

## How it was checked

- `test:` references need `tested`. Every cited test (69 test IDs) was
  run with `pytest -W error` at `main` efabc22. They all passed except the
  two `test_v2_client_exercises_every_published_tool` cases. Those need the
  `semantic` extra, which the local environment lacked, and they passed in
  CI on #163.
- The other kinds need `structural` evidence: the named artifact exists.
  Every file locator was checked to exist, and every symbol locator to be
  defined in its file.
- `MCP-V2-AC6`'s `test:full-warning-strict` points at the CI workflow,
  which runs the whole suite with `-W error` on three operating systems.

## Weak matches, stated plainly

Some references name a test that was never written under that exact name.
They cite the closest existing test instead:

- `test:unmatched-reality-is-not-deletion` and `test:evidence-gated-diff`
  share `test_safe_diff_requests_review_and_never_infers_creation_or_deletion`.
- `test:mcp-v2-cwd-isolation` cites tests that assert the working directory
  is unchanged after tool calls. No test is dedicated to it.
- `test:intent-consistency-mcp-contract` cites the v2 public-surface test,
  which only checks that `check_intent_consistency` is published.

## Triage decisions

Recording evidence changes the plan digest, so the 27 decisions in
`../mapping-triage-2026-11-08/decisions.json` went stale. `decisions.json`
here binds the same decisions, unchanged, to the new digest, as that record
instructs. Afterwards triage reports 9 authorized items, all
`missing_implementation`, and 0 needing evidence.
