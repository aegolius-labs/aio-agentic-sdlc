# AIO Agentic SDLC Roadmap

Last updated: 2026-11-08

## Product goal

Reach the North Star in [`doc/VISION.md`](doc/VISION.md). The backlog is the
diff between the Intention DAG and the Reality DAG, and agents close that diff
autonomously within the approval gates of
[`doc/authority-model.md`](doc/authority-model.md).

## What this document is

This roadmap is a human-readable sequence over the work. It is not a second
source of intent. What the software should be lives in
`.aio-agentic-sdlc/intention-dag.yaml`, and the work is the diff computed from
it. Where an item names an Intention node, that node is authoritative and this
file only orders it. An item with no node is a proposal until the Intake path
records it as intent.

## Progress rules

- A milestone is complete only when each outcome has observable evidence: a
  merged pull request, a test, or a change record under
  `.aio-agentic-sdlc/changes/`.
- Mark an outcome `[x]` only when it was met. Use `[-]` for an outcome retired
  unmet, and say why and where it now lives. Never narrow an outcome to close
  it.
- Approving intent, approving a mapping, and recording a triage decision are
  human decisions. The roadmap never treats them as done on an agent's word.
- Update the date whenever an item changes state.

## Definition of done for the vision

The vision is reached when all of the following hold on this repository
itself:

1. Every Intention node is `approved`, `rejected` or retired. None is left at
   `review_required` by default.
2. Reconciliation can tell done from missing: every approved node is either
   confirmed against Reality or classified by triage.
3. "Done" means the node's acceptance criteria have the evidence they require,
   not only that a source mapping exists.
4. A new want stated by a person flows through Intake into approved intent,
   appears in the diff, is executed by `aio-sdlc apply`, and comes back as
   evidence, without hand-editing any state file.
5. The work projects one way to GitHub through `agentic-backlog-kit` (Seam A),
   and QA findings return through `agentic-qa-kit` with an explicit
   disposition (Seam B).

## Completed foundations

- [x] Versioned, locked, journaled local state (ADR 0001).
- [x] Intent IR v1 with approval states and revision history (ADR 0002).
- [x] Evidence-gated reconciliation baseline (change record
  `evidence-gated-reconciliation`).
- [x] Approval-gated source mapping and receipts (`approval-gated-source-mapping`,
  `approved-source-mappings`, `human-readable-mapping-review`).
- [x] Legacy Intent IR migration: all 61 nodes carry Intent IR
  (`legacy-intent-ir-migration`).
- [x] Drift triage with digest-bound decisions (`drift-triage`).
- [x] DAG visualization and comparison (`dag-visualization-comparison`).
- [x] MCP SDK v2 server (`mcp-sdk-v2`).
- [x] Explicit source identity maintenance (`source-identity-maintenance`).
- [x] Seam A return channel: `dag-tool reconcile --observed-state` reads
  `abk observe` evidence.
- [x] `aio-sdlc apply` executes only triage-authorized work (#132).

## M1: Intent review

Goal: the diff can authorize work. Since the owner's review on 2026-11-05
(#145), 45 nodes are approved, 6 rejected and 11 still `review_required`, so
intent approval no longer blocks most of the diff. As of 2026-11-08 the
blocker is classification: 35 approved items await a mapping or a triage
decision (M2).

- [ ] Review all 55 `review_required` nodes: approve, revise or retire each.
  The grouped proposal is in
  [doc/reviews/intent-review-2026-10-15.md](doc/reviews/intent-review-2026-10-15.md).
  45 were decided in #145; 11 remain, deferred by that review.
- [x] Resolve the nodes that contradict other documents: the licensing and
  EULA nodes against `COMMERCIAL.md`, and the QA swarm nodes against the
  authority model's layer 5. Rejected or revised in #145.
- [ ] Replace the mechanically copied acceptance criteria on approved nodes
  with criteria that name their required evidence.
- [x] Intention DAG self-consistency check as a new read-only tool (#12).

## M2: Mapping coverage

Goal: reconciliation resolves most nodes in both directions. As of
2026-11-08, 18 of 62 nodes are confirmed against 373 Reality nodes.

- [x] Map every approved node that has an implementation, through the
  read-only review and approval flow. The owner's 2026-11-08 packet mapped 8
  and classified the rest (`changes/mapping-triage-2026-11-08/`).
- [x] Refresh stale mapping receipts after source edits, and make the stale
  state visible in CI so it does not accumulate. `dag-tool mapping receipt
  check` reports every stale receipt, and CI fails on one.
- [ ] Emit `depends_on` relationships for component endpoints in the Reality
  parser, or record them as a permanent observation limit (two items are
  `framework_tooling_drift` today).
- [ ] Observe agents, containers, directories and data files, or record them
  as a permanent observation limit. They account for most of the 32
  `framework_tooling_drift` items.
- [ ] Make triage decisions durable per subject, so an owner's decision isn't
  re-derived each time the whole-DAG digest changes.

## M3: Evidence decides done

Intention node: Explicit Evidence Model (`6b1b3459`).

- [x] Completion distinguishes declared, mapped, structural, tested,
  behaviorally verified and approved evidence (ADR 0003).
- [x] A confirmed node whose acceptance criteria lack their required evidence
  stays in the diff as a `verify_acceptance` task, which triage authorizes
  for approved intent as `acceptance_evidence_required`.
- [x] `apply` marks a task complete only on evidence, not because an agent
  call returned. A finished agent call leaves the task blocked as awaiting
  evidence until it leaves the diff.
- [x] A person approves finished work before it completes (Approval Gate,
  `40566eb0`; Operational Modes Config, `7b029abd`). Work that leaves the
  diff waits for `aio-sdlc approve`; `approval_mode: bypass` in
  `config.json` completes it on its own for continuous delivery.

## M4: The closed loop

Intention nodes: Intent Translation Benchmark (`d64fbc3a`), Closed-loop
Reference Demo (`cb02a996`).

- [ ] Intake turns a stated want into a reviewable Intention node through the
  Intent IR tools.
- [x] The backlog equals the diff: tasks that leave the diff leave the
  execution queue instead of accumulating, and a completed task that
  reappears in the diff reopens.
- [x] A fresh checkout reproduces one requirement through intent,
  implementation, tests, evidence and approval. `dag-tool demo`, with an
  integration test, and CI runs it from the installed wheel. Its traceability
  report still needs an outside reader's review (DEMO-AC2).
- [ ] A versioned golden corpus measures intent translation.
  `dag-tool benchmark-intent` and corpus v1 exist; the corpus and its
  thresholds wait for the owner's approval (BENCHMARK-AC1).

## M5: Federation seams

- [x] Seam A forward direction: export derived work as an
  `agentic-backlog-kit` manifest carrying canonical GUIDs, with fixtures held
  on both sides. `dag-tool export-abk`, contract `seam-a-work` v1.
- [ ] Seam B: a QA finding inside accepted intent reverts the responsible
  node (`revert-node`) through an approval-gated transition, and only findings
  outside intent become Bug payloads.

## M6: Portability and hardening

Intention nodes: Agent Runtime Portability (`4f6cdecf`), Cross-language
Ontology Portability (`15302505`), Product Hardening (`82579715`).

- [x] Agent invocation sits behind a runtime adapter (`agent_runtime`):
  `antigravity` or any agent CLI through `command`, chosen by configuration.
  `google-antigravity` is now an optional extra.
- [x] Python and TypeScript parsers emit the same core ontology.
  `tests/test_typescript_parser.py` checks one project written in both
  languages (`tests/fixtures/mixed-python-typescript`) and GUID traceability
  across them. Still open: the ontology-boundary review (ONTOLOGY-AC2) is the
  owner's, and `dag-tool mapping` writes and checks receipts in Python source
  only, so a TypeScript symbol takes its identity from a hand-written marker.
- [ ] A clean environment installs and validates the CLI, MCP server and both
  host plugins through documented contracts. CI installs the wheel alone and
  runs `dag-tool doctor`, which performs a real MCP handshake, and installs
  the Claude Code plugin into an empty profile
  ([install contract](doc/install-contract.md),
  [recovery](doc/recovery.md)). The Codex plugin has no validator CI can run,
  so it is covered only by the manifest parity tests.
- [ ] Proposal, no Intention node yet: record opt-in usage evidence under the
  organization's
  [usage evidence contract](https://github.com/aegolius-labs/.github/blob/main/docs/usage-evidence.md).
  `dag-tool` and `aio-sdlc` append one event per command in a project that
  opted in, and nothing from the project itself. Usage is evidence about this
  framework as a product, never intent. The owner approved the route on
  2026-11-07; it becomes work only once Intake records it as a node.
