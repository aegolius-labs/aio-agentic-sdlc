# AIO Agentic SDLC Roadmap

Last updated: 2026-10-15

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

Goal: the diff can authorize work. Today triage withholds 52 of 56 items
because their intent is `review_required`.

- [ ] Review all 55 `review_required` nodes: approve, revise or retire each.
- [ ] Resolve the nodes that contradict other documents: the licensing and
  EULA nodes against `COMMERCIAL.md`, and the QA swarm nodes against the
  authority model's layer 5.
- [ ] Replace the mechanically copied acceptance criteria on approved nodes
  with criteria that name their required evidence.
- [x] Intention DAG self-consistency check as a new read-only tool (#12).

## M2: Mapping coverage

Goal: reconciliation resolves most nodes in both directions. Today 10 of 61
nodes are confirmed against 322 Reality nodes.

- [ ] Map every approved node that has an implementation, through the
  read-only review and approval flow.
- [ ] Refresh stale mapping receipts after source edits, and make the stale
  state visible in CI so it does not accumulate.
- [ ] Emit `depends_on` relationships for component endpoints in the Reality
  parser, or record them as a permanent observation limit (two items are
  `framework_tooling_drift` today).

## M3: Evidence decides done

Intention node: Explicit Evidence Model (`6b1b3459`).

- [ ] Completion distinguishes declared, mapped, structural, tested,
  behaviorally verified and approved evidence.
- [ ] A confirmed node whose acceptance criteria lack their required evidence
  stays in the diff.
- [ ] `apply` marks a task complete only on evidence, not because an agent
  call returned.

## M4: The closed loop

Intention nodes: Intent Translation Benchmark (`d64fbc3a`), Closed-loop
Reference Demo (`cb02a996`).

- [ ] Intake turns a stated want into a reviewable Intention node through the
  Intent IR tools.
- [ ] The backlog equals the diff: tasks that leave the diff leave the
  execution queue instead of accumulating.
- [ ] A fresh checkout reproduces one requirement through intent,
  implementation, tests, evidence and approval.
- [ ] A versioned golden corpus measures intent translation.

## M5: Federation seams

- [ ] Seam A forward direction: export derived work as an
  `agentic-backlog-kit` manifest carrying canonical GUIDs, with fixtures held
  on both sides.
- [ ] Seam B: a QA finding inside accepted intent reverts the responsible
  node (`revert-node`) through an approval-gated transition, and only findings
  outside intent become Bug payloads.

## M6: Portability and hardening

Intention nodes: Agent Runtime Portability (`4f6cdecf`), Cross-language
Ontology Portability (`15302505`), Product Hardening (`82579715`).

- [ ] Agent invocation sits behind a runtime adapter. Today the loop imports
  `google.antigravity` directly.
- [ ] Python and TypeScript parsers emit the same core ontology.
- [ ] A clean environment installs and validates the CLI, MCP server and both
  host plugins through documented contracts.
