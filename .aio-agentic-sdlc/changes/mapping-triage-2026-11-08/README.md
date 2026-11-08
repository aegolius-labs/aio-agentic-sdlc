# Mapping and triage decisions, 2026-11-08

Felix decided these on three decision cards on 2026-11-08:

1. At 19:08:23 UTC he approved a review packet. It proposed 8 mappings, 2
   receipt refreshes, 10 `missing_implementation` decisions and 17
   `framework_tooling_drift` decisions for the approved items that triage
   listed as needing classification.
2. At 19:50:53 UTC, after three packet mappings changed before they were
   written, he approved two of them again at their new evidence digests
   (`MappingEngine.refresh_receipt`, `cli.main`). He recorded the DAG Schema
   Migrator as `framework_tooling_drift`, because `cli.py` can hold only one
   mapping receipt.

Six packet mappings were written at the first approval and two at the second.
Their receipts in the source files are the record of those approvals.
`dag-tool mapping receipt check` reports 15 fresh receipts.

`decisions.json` holds the triage decisions. It binds to the whole-DAG plan
digest, so any change to the Intention DAG, the Reality DAG or the evidence
ledger makes it stale. Re-derive it from this record when that happens.

## Held back

- **Version Command.** The packet proposed `missing_implementation` because
  `--version` did not exist. #158 has since added it to both CLIs, and the MCP
  server already reports its version on initialization, so recording
  "missing" would have authorized work that is done. At 19:57:28 UTC Felix
  chose `framework_tooling_drift` on a third card instead.
- **Canonical GUID Extractor mapping.** It is only a partial match, because
  agent-frontmatter markers aren't read. It is classified
  `missing_implementation` instead.

## Updated reasons

Two reasons changed since the packet. The classification of each stayed the
same.

- **Agent Runtime Portability.** RUNTIME-AC1 is met by `agent_runtime` (#157).
  RUNTIME-AC2 is still open.
- **Product Hardening.** CI now checks a clean wheel install of the CLI
  (#160). The MCP server, the host plugins and HARDENING-AC2 are still open.
