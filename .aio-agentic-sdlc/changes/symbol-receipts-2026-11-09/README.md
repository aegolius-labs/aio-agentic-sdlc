# Symbol-bound mapping receipts (2026-11-09)

On 2026-11-09 the owner chose, on a decision card, to bind mapping receipts to
the mapped symbol instead of the whole file. This record covers the change and
the work that followed from his other two answers that day.

## What changed

- A new or refreshed receipt carries `symbol_sha256`, the digest of the mapped
  definition's own lines, decorators included. Editing the rest of the file
  leaves it fresh; editing or renaming the symbol makes it stale.
- The 15 receipts written before that carry no `symbol_sha256` and stay bound to
  the whole file until refreshed.

## Batch refresh waiting for the owner

The card's chosen option says the owner approves one batch refresh of all the
older receipts after the change is built. `refresh-batch.json` lists each one
with the digest of its fresh `dag-tool mapping receipt review`. A refresh only
rebinds the receipt; it never changes the identity the owner approved.

| Intention node | File | Symbol | Status | Review digest |
| --- | --- | --- | --- | --- |
| PRD Archiver | `src/aio_agentic_sdlc/archiver.py` | class PRDArchiver | fresh | `0db8d49e418b` |
| CLI Entrypoint | `src/aio_agentic_sdlc/cli.py` | function main | fresh | `85e4f9d90a8d` |
| Traceability Validator | `src/aio_agentic_sdlc/core.py` | class TraceabilityValidator | fresh | `63b8d4bcc40b` |
| Diffing Engine | `src/aio_agentic_sdlc/diffing_engine.py` | class DiffingEngine | fresh | `048176937850` |
| Explicit Evidence Model | `src/aio_agentic_sdlc/evidence.py` | class EvidenceEvaluator | fresh | `756ba51565a3` |
| Intention DAG Consistency Check | `src/aio_agentic_sdlc/intent_consistency.py` | class IntentConsistencyChecker | fresh | `b460c75313ae` |
| Intent IR v1 | `src/aio_agentic_sdlc/intent_ir.py` | class IntentIR | fresh | `78b1a66ee1d3` |
| Legacy Intent IR Migration | `src/aio_agentic_sdlc/intent_migration.py` | class LegacyIntentMigrator | fresh | `e70d5a096642` |
| Explicit Source Identity Maintenance | `src/aio_agentic_sdlc/mapping.py` | function refresh_receipt | stale | `30f44d8b2e36` |
| MCP SDK v2 Integration | `src/aio_agentic_sdlc/mcp_server.py` | class _SanitizingMCPServer | fresh | `1d754a1b9e8e` |
| Reality DAG Generator | `src/aio_agentic_sdlc/reality_dag_generator.py` | class RealityDAGGenerator | fresh | `dcc9c4f6970a` |
| Artifact Templating Engine | `src/aio_agentic_sdlc/templating_engine.py` | function generate_document | fresh | `7f07efc83b3c` |
| Parser Factory | `src/aio_agentic_sdlc/parsers/factory.py` | class ParserFactory | fresh | `0382b410a7e1` |
| Markdown Parser | `src/aio_agentic_sdlc/parsers/markdown_parser.py` | class MarkdownAgentParser | fresh | `594f65248050` |
| Tree-Sitter Parser | `src/aio_agentic_sdlc/parsers/python_parser.py` | class TreeSitterParser | fresh | `c726271d43fa` |

`refresh_receipt` is stale because this change edits that function: it now
writes `symbol_sha256`.

## Closed-loop demo mapping

The owner approved `ClosedLoopDemo` as the implementation identity of the
Closed-loop Reference Demo node (`cb02a996`) at evidence digest
`541a3da0d59f3a82aeec201a7f967b614d28419307dd3f8591a0166db0c394d9`, the same
digest his card showed. The receipt is the first symbol-bound one.

Evidence recorded afterwards:

| Criterion | Reference | Level | Locator |
| --- | --- | --- | --- |
| DEMO-AC1 | `test:closed-loop-integration` | tested | `tests/test_closed_loop_demo.py` |
| DEMO-AC1 | `demo:closed-loop-reproduction-script` | behaviorally_verified | the Clean install CI job |
| DEMO-AC2 | `artifact:human-readable-traceability-report` | structural | `src/aio_agentic_sdlc/traceability.py` |

`review:external-reader-usability` stays open: the owner chose to have an
outside reader review the report later. Triage therefore keeps the demo as
`acceptance_evidence_required` for DEMO-AC2.

## Triage decisions

Reality was regenerated, so the mapping and the evidence changed the plan
digest. `decisions.json` binds the same owner decisions to the new digest, minus
the demo's `missing_implementation` decision, which no longer applies now that
the node is confirmed. Triage then authorizes 8 `missing_implementation` items
and the demo's evidence item.
