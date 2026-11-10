# Approval Gate (2026-11-10)

On 2026-11-09 the owner chose to gate completion, on by default, with
`approval_mode: bypass` in `config.json` restoring automatic completion. This
builds the Approval Gate (`40566eb0`) and Operational Modes Config
(`7b029abd`).

## Receipts waiting for the owner

Two mapped symbols change, so their symbol-bound receipts are stale until the
owner approves a refresh:

| Intention node | Symbol | Why it changed | Review digest |
| --- | --- | --- | --- |
| CLI Entrypoint | `main` in `src/aio_agentic_sdlc/cli.py` | registers `aio-sdlc approve` | `3b2f67c1de2e` |
| Closed-loop Reference Demo | `ClosedLoopDemo` in `src/aio_agentic_sdlc/closed_loop_demo.py` | adds the fifth gate | `c33bda0c22c0` |

`refresh-batch.json` holds the full digests. `core.py` also changes, but only
outside `TraceabilityValidator`, so its receipt stays fresh: the first
symbol-bound receipt to survive an edit to its file.

## Not changed

Reality and the triage decisions are not regenerated here, so the decisions in
`../symbol-receipts-2026-11-09/decisions.json` stay current. Mapping these two
nodes to `approval_gate` code is a separate owner decision.
