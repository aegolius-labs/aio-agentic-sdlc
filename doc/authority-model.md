# Aegolius Labs authority model

This document is the single normative statement of which repository owns which
kind of truth. It exists because three Aegolius Labs repositories overlap in
subject matter and would otherwise contradict each other:

- `aio-agentic-sdlc` — the Dual-DAG reconciliation engine and SDLC orchestrator.
- `agentic-backlog-kit` (ABK) — deterministic GitHub Issues and Projects backlog
  workflows.
- `agentic-qa-kit` (AQK) — evidence-centered quality assurance workflows.

ABK and AQK were extracted from concepts in this repository so that a developer
could use a fast, targeted, dependency-free tool without adopting the whole
framework. They remain independently installable. This document defines how all
three compose when they are used together, and it takes precedence over any
narrower statement in an individual repository.

## The authority ladder

| Layer | Artifact | Owner | Kind of truth |
| --- | --- | --- | --- |
| 1 | `.aio-agentic-sdlc/intention-dag.yaml` | `aio-agentic-sdlc` | What the software **should** be. Durable, version-controlled intent. |
| 2 | `.aio-agentic-sdlc/reality-dag.yaml` | `aio-agentic-sdlc` | What the software **is**. Regenerable observation. Evidence, not intent. |
| 3 | `.aio-agentic-sdlc/backlog.json` | `aio-agentic-sdlc` | The **work**: the evidence-gated diff between layers 1 and 2. Derived and authoritative for execution. |
| 4 | `.agentic-backlog/manifest.json` and GitHub | `agentic-backlog-kit` | A **projection** of layer 3 for human and team visibility. Never authoritative. |
| 5 | `.agentic-qa/` session ledger | `agentic-qa-kit` | **Evidence about reality**: bounded attempts, findings, reproductions, limitations. |

Authority flows strictly downward. A lower layer may never select, override, or
silently edit a higher one.

## The governing rule

> **Downstream state flows back as evidence, never as intent.**

A closed GitHub issue, a moved Project card, a green CI run, or a confirmed QA
finding is an *observation about reality*. It may inform layer 2 or layer 3. It
may never edit layer 1. Changing what the software is supposed to be is always
an explicit, approval-gated Intent IR transition performed by this framework's
own tooling.

This rule is what makes ABK's "GitHub is the operational system of record" and
this framework's "external trackers are not authoritative" both true at once.
They are statements about different layers:

- Within ABK's own scope, GitHub *is* the system of record: ABK holds no second
  live board and defers to GitHub for every managed issue's real state.
- Within the composed system, ABK's scope is layer 4. It is the record of the
  *projection*, not of the *intent*.

`doc/VISION.md` already anticipates this: remote projections are permitted as
one-way projections "whose contents cannot override locally derived work." ABK
is the sanctioned implementation of that projection.

## Composition boundaries

### aio-agentic-sdlc owns

Intent capture and approval, Intent IR, canonical GUID traceability, Reality DAG
generation, evidence-gated reconciliation, drift triage, spec promotion, and
agent orchestration across the SDLC roles.

### agentic-backlog-kit owns

Work-item hierarchy (`Initiative -> Epic -> Feature -> Story/Bug -> Task`),
deterministic Impact/Effort/Business-Value/Enabler-Value scoring, dependency-safe
capacity planning, and the digest-bound `plan -> confirm -> apply -> receipt`
contract for reconciling that work with GitHub Issues and Projects.

ABK does not decide *what* should be built. When composed, it receives work.

### agentic-qa-kit owns

Bounded QA sessions, charters, attempts, findings, controlled reproduction, and
the auditable evidence ledger. AQK does not decide disposition on its own and
does not manage a backlog.

## Interface contracts

Two seams connect the three repositories. Each is a data contract with fixtures
held on **both** sides, so neither repository imports the other at runtime or at
test time.

### Seam A: work projection (layer 3 to layer 4)

`aio-agentic-sdlc` derived backlog item -> ABK manifest item -> GitHub.

The models share a lineage but differ deliberately:

| Concern | aio-agentic-sdlc | agentic-backlog-kit |
| --- | --- | --- |
| Graph node types | architectural (`system`, `container`, `module`, `component`, `endpoint`, `entity`, `agent`) | not modeled |
| Work item hierarchy | `Epic -> Feature -> Task/Bug` | `Initiative -> Epic -> Feature -> Story/Bug -> Task` |
| Scoring inputs | `impact`, `effort`, `category` | `impact`, `effort`, `business_value`, `enabler_value` |
| Dependencies | `requires` edges | native GitHub issue dependencies |
| Identity | canonical GUID | stable ABK item ID, plus a hidden issue-body marker |

The projection is therefore lossy in one direction by design. The canonical GUID
must be carried into the ABK item and into the GitHub issue body marker so that
a projected issue can always be traced back to its Intention DAG node.

Projection is **one-way**. ABK's existing additive, update-only apply semantics
already satisfy this: it never deletes issues, removes relationships, archives
Project items, or closes issues automatically.

### Seam B: QA evidence (layer 5 to layers 2-4)

An AQK finding has exactly two legitimate dispositions, and the composed system
must choose explicitly:

- **`revert-node`** — the defect falls inside existing accepted intent. The
  correct action is to revert the responsible Intention DAG node to an open
  state so the diff regenerates the work. No new work item is created. This is
  the default inside a full `aio-agentic-sdlc` pipeline and matches the
  `sdlc_qa` role's revert logic.
- **`bug-handoff`** — the defect falls outside modeled intent, or AQK is being
  used standalone without this framework. AQK emits one Bug payload for ABK
  ingestion.

AQK must record which disposition was chosen and why. Emitting a Bug payload for
a defect that belongs to an existing accepted node is a contract violation: it
creates a second, competing record of the same work.

## Standalone use

Each repository remains independently valid and installable:

- **ABK alone** — GitHub is the system of record outright. Layers 1-3 do not
  exist. This is the fast, targeted, zero-dependency configuration.
- **AQK alone** — the evidence ledger stands on its own; `bug-handoff` is the
  only disposition available.
- **This framework alone** — layers 4 and 5 are simply absent.

Standalone use is a supported product configuration, not a degraded mode. This
is deliberately why the kits were not merged into this repository: both keep a
zero-runtime-dependency standard-library implementation, while this framework
carries a substantial dependency set. Merging would impose that dependency set
on the targeted use case that motivated the extraction.

## Revisiting this decision

Federation is the current decision, not a permanent one. Consolidation into this
repository should be reconsidered when any **two** of the following hold:

1. The Seam A or Seam B contract requires breaking changes more often than
   quarterly, indicating the boundary is not real.
2. The same scoring, cycle-detection, or hierarchy-validation defect is fixed
   independently in two repositories more than twice.
3. No standalone installation of ABK or AQK occurs over a six-month period,
   indicating the targeted use case is hypothetical.

Until then, the cost of federation is this document and the two contract fixture
sets. That cost is lower than a rewrite, and it preserves ABK's published
release and both kits' dependency-free guarantee.
