# aio-agentic-sdlc: Intention node review packet

> Moved into the repository on 2026-11-02 so ROADMAP M1 can be worked from
> here. Counts and IDs are as of `main` at 88a50ad on 2026-10-15; re-measure
> with `dag-tool intent-summary` before acting on them.

Prepared 2026-10-15 from `main` at 88a50ad. 55 of 61 Intention nodes are
`review_required`, and drift triage withholds all work on them. Only the owner
can approve intent. Nothing here had been changed when it was written.

**How to answer:** the owner answers with group letters, for example
"approve A and B, retire D, C3 revise", naming single nodes by their short ID.
Each transition is then recorded through `dag-tool intent set` with the owner
as approver, one revision per node, in a reviewable PR.

**What approval means:** "this is what the software should be." It does not
mean the code is done. Approved intent with no code becomes real
implementation work in the diff, which is the point.

**One caveat for every group:** the legacy migration copied each node's
description into its single acceptance criterion. Approving as-is accepts
that weak criterion. The suggestion is to approve now and propose sharper
criteria as a later revision, which goes back to the owner.

## A. Approve: built and matching the code (24)

The code exists and does what the node says.

| ID | Node | Type | Evidence |
| --- | --- | --- | --- |
| 4d76717e | AIO Agentic SDLC System | system | The repository itself |
| cb432b58 | DAG Engine Container | container | `dag_manager`, `diffing_engine`, `reconciliation` |
| fa35fa8a | Diffing Engine | component | `DiffingEngine`, mapping receipt exists |
| 0fea8fea | Reality DAG Generator | component | `reality_dag_generator.py` |
| d0307d83 | Parser Factory | component | `parsers/factory.py` |
| 9865715b | Tree-Sitter Parser | component | `parsers/python_parser.py` |
| a937dc0f | Markdown Parser | component | `parsers/markdown_parser.py` |
| 7418a0a0 | AST Visitor | module | `parsers/visitors.py` |
| 2e8a1562 | Canonical GUID Extractor | component | `parsers/python_parser.py`, `source_markers.py` |
| 685b1d12 | Traceability Validator | component | `core.TraceabilityValidator`, receipt exists |
| 2499ec97 | DAG Schema Migrator | component | `aio-sdlc migrate-ids` |
| f1009cfe | MCP Server | container | `mcp_server.py`, 23 tools |
| 54b91d55 | Agentic Orchestrator Loop | container | `orchestrator_loop.py`, gated on triage by #132 |
| f24b7477 | CLI Entrypoint | component | `cli.py`; see C4 about its dependency edges |
| 6506870b | PRD Archiver | component | `archiver.py` |
| 5a81e63d | Artifact Templating Engine | component | `templating_engine.py` |
| a6cf0410 | Templates Directory | entity | `src/aio_agentic_sdlc/templates/` |
| d4049c0c | Inbox Directory | entity | `.aio-agentic-sdlc/inbox/` |
| 908d2539 | Archive Directory | entity | `.aio-agentic-sdlc/archive/` |
| c2d35f1b | Specs Directory | entity | `.aio-agentic-sdlc/specs/` |
| 6ff0c1eb | Research Spikes Directory | entity | `.aio-agentic-sdlc/research-spikes/` |
| 64b5afea | Unified Configuration File | entity | `config.json` |
| 277fe548 | Unified Agent Definitions | entity | `.agents/agents/*/agent.md` |
| 7bcd1683 | Intent IR v1 | component | ADR 0002, `intent_ir.py` |

## B. Approve as wanted, not built yet (11)

These are VISION-aligned. Approving them makes them real work in the diff.

| ID | Node | Type | Note |
| --- | --- | --- | --- |
| 6b1b3459 | Explicit Evidence Model | component | Lets acceptance evidence, not just a mapping, decide "done" |
| d64fbc3a | Intent Translation Benchmark | component | Measures the Intake step |
| cb02a996 | Closed-loop Reference Demo | component | Proves the whole loop end to end |
| 4f6cdecf | Agent Runtime Portability | component | Today the loop is tied to `google.antigravity` |
| 15302505 | Cross-language Ontology Portability | component | TypeScript parser |
| 82579715 | Product Hardening | component | Install, contracts, CI, recovery |
| 22822d50 | SDLC Intake Agent | agent | Role exists; the human-want-to-node path is the VISION loop's entry |
| 07e7e16c | SDLC Architect Agent | agent | Role exists; `plan` invokes it on inbox PRDs |
| bcb5855b | SDLC Researcher Agent | agent | Role exists |
| 48295997 | Implementer Agent | agent | Role exists; Variance Reports not built |
| 40566eb0 | Approval Gate | component | Pre-merge human gate; partly covered by triage |

## C. Owner's product call (12, plus edges on one A node)

These conflict with another document, overlap another kit, or are scope
questions only the owner can answer. The suggestion is in the last column.

| # | ID | Node | Why it needs the owner | Suggest |
| --- | --- | --- | --- | --- |
| C1 | 900f5127 | Commercial Licensing Enforcer | `COMMERCIAL.md` says commercial rights come from a signed agreement, not key enforcement | Retire |
| C1 | da3ee4cb | Merchant of Record API | Same as above | Retire |
| C1 | 3ea4e322 | EULA & Privacy Prompt | Same, plus the plugins install non-interactively | Retire |
| C2 | a187faf6 | Telemetry Module | A network client in a local tool; no code exists | Retire or defer |
| C2 | 415fa500 | Telemetry Backend | Same | Retire or defer |
| C3 | f4d2f082 | QA Swarm Orchestrator | Overlaps agentic-qa-kit's layer 5 under the authority model | Revise to "consume AQK evidence via Seam B" |
| C3 | 54a600df | Specialized QA Agents | Same overlap | Revise or retire |
| C4 | f24b7477 | CLI Entrypoint edges | Calls EULA, Licensing, Daemon and Version nodes that do not exist | Drop those edges with C1/C5 |
| C5 | 10d4c0ba | Daemon Watcher | Long-running process; nothing exists | Defer |
| C5 | 09497db1 | TUI Dashboard | DAG visualization already covers read-only views | Defer |
| C5 | ea4ceb31 | Shared State Store | Only feeds the TUI | Same as TUI |
| C6 | 1525a991 | Health Check Endpoint | The MCP server is stdio; a liveness probe has no consumer | Retire |
| C6 | 989b390d | Version Command | No `--version` exists today | Approve |

## D. Approve or retire: parallel-execution design (7)

These describe a parallel swarm the code does not attempt. They are coherent
with VISION point 4 but large. Approving them puts them in the diff.

| ID | Node | Type |
| --- | --- | --- |
| 9066081a | Parallel Task Runner | component |
| 5a916efe | Conflict Resolution Manager | component |
| 483abc2c | Variance Report Router | component |
| b9c4304e | Session Report Compiler | component |
| b4e6a8f3 | Subagent Output Templates | entity |
| 7b029abd | Operational Modes Config | entity |
| 45b34e7b | Agent Personas Config | entity |

Suggest: approve 7b029abd with the Approval Gate, defer the rest behind the
Closed-loop Reference Demo.

## Outside the groups

- 37c790a3 **Agent Format Migrator** described a one-time migration that has
  happened: no legacy `agent.json` remains. Suggest retire.
- 2131072d **Intention DAG Consistency Check** is new (added with #134 for issue #12). Its criteria name real evidence. Suggest approve.
- The 6 approved nodes are untouched.
