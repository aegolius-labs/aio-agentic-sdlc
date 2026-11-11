# Seam B, framework side (2026-11-11)

Builds QA Evidence Intake (`f4d2f082`), QA-SEAM-B-AC1, on this side of the
seam: the `aqk-findings` contract version 1, its fixture, and `dag-tool qa
propose` and `dag-tool qa record`. The contract is in
`doc/authority-model.md`.

## Why the work was authorized

Felix classified QA Evidence Intake as `missing_implementation` on the
2026-11-08 decision card
(`.aio-agentic-sdlc/changes/mapping-triage-2026-11-08/decisions.json`). That
decision set is bound to an older plan digest and is stale. Its README says to
re-derive it from that record. Rebound to plan digest `bbb77f6a` (the state
before this change), Felix's decision alone makes triage report the node as
`missing_implementation` with `implementation_authorized: true`. The work was
added to the local backlog with `aio-sdlc add` and claimed with `aio-sdlc
status ... "In Progress"`. No new triage decision was made, and the rebound
set is not committed.

## How `revert-node` reopens work

A recorded `revert-node` disposition lives in the evidence ledger beside the
records it overrides. It reopens one acceptance criterion: records made before
it stop counting for that criterion, so the node returns to the diff as a
`verify_acceptance` task, which triage authorizes for approved intent. It ends
when records made after it meet each reference again. The Intention DAG is
never written, so approved intent stays approved. Because the dispositions are
in the ledger, triage's evidence digest covers them.

## Waiting on the owner

- `EvidenceEvaluator` changed, so its mapping receipt is stale and
  `dag-tool mapping receipt check` fails CI until it is refreshed.
  `refresh-batch.json` holds the review digest for that decision. The identity
  is unchanged: the class still grades acceptance evidence.
- QA Evidence Intake is a `module` node. The mapping tools approve Python
  classes and functions only, and reject `qa_findings.py` as a candidate
  (`candidate source kind is not supported`). The node needs a decision: a
  `framework_tooling_drift` classification, like the other unobservable
  nodes, or another identity.
- `fixture:seam-b-contract` needs `behaviorally_verified` evidence. It can be
  recorded once the kit holds the fixture byte-identically and its export
  emits it. `test:seam-b-disposition` is `tests/test_seam_b_findings.py`.
