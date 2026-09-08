---
document_type: sdd
title: "MCP v2 and Source Identity Implementation Variance"
author: "Codex orchestrator after independent framework QA"
date: "2026-09-08"
related_prd: ".aio-agentic-sdlc/changes/mcp-sdk-v2/prd.md"
node_id: "86367041-79ce-5415-b107-ef60cf721bf3"

---
# MCP v2 and Source Identity Implementation Variance

## 1. Architecture Overview

This addendum records implementation mechanics that supersede the corresponding mechanics in
`task-86367041-79ce-5415-b107-ef60cf721bf3.md` section 2.5 and `../source-identity-
maintenance/sdd.md` section 2.3. It does not rewrite the original requirements or approval
history. The source-identity capability remains `15019926-c6be-5c98-b558-954c7657e5c6`,
implemented through its existing MappingEngine parent. QA identified these documentation
differences after the corrective code review.

## 2. System Components

1. Reality generation invokes the installed `RealityDAGGenerator` in-process under the canonical
   DAG lock, rechecking the output path after scanning. It no longer spawns a target
   repository's `uv run dag-tool`; a bare external repository needs neither a Python project nor
   a local executable.
2. Mapping, document replacement, and spec promotion stage content in private `.aio-agentic-
   sdlc/backups/` subdirectories, then use atomic no-overwrite moves. They retain originals,
   partial staging files and concurrent occupants for recovery. They do not delete public-path
   occupants after a separate identity check. This replaces the original same-directory
   staging/replace/cleanup mechanics because independent adversarial review demonstrated data-
   loss races.
3. Semantic cache access uses project-scoped process and file locks. Initialization closes
   failed connections and reports bounded SQLite prerequisites through MCP. Native macOS CI
   exposed a system Python without extension support; the CI matrix now requires UV-managed
   Python rather than skipping real vector queries.

## 3. Data Model

No canonical DAG, Intent IR, backlog, mapping receipt or public protocol schema is changed by
these corrections. The original 21-operation baseline is expanded only by the two separately
accepted source-receipt operations, for 23 total tools. Recovery files are ignored, non-
authoritative copies, not accepted specifications. They accumulate until explicit cleanup after
checking canonical data and ensuring no writers are active; unsupported cross-filesystem moves
fail without overwrite.

## 4. API Design

CLI, MCP tool names and stdio entry point remain stable. The Python document generator accepts
an optional `project_path` to locate private recovery storage; MCP passes the explicit project
root. The initial flat `promote_spec` filename contract remains unchanged. Nested change-
workspace promotion is roadmap 1.9, not silently added or manually bypassed here.

Verification: local warning-strict suite 418 passed; independent framework QA reran 37
acceptance/security tests successfully. Tests use real v2 auto/legacy clients, stdio, SQLite
vector queries, and forced filesystem transition races. The cross-platform pinned-descriptor
fixture substitutes only the first handle; all later snapshot reads inspect actual file bytes,
including Linux inode reuse. Native CI and independent final-head review remain required; local
results alone do not authorize release.

## 5. Security Considerations

No-overwrite moves preserve competing data, but multiple filesystem operations are not a single
crash-atomic transaction. Failures can leave private recovery artifacts and require inspection;
restoration never overwrites a new public occupant. Tests verify original and concurrent byte
sets, late in-place edits, path substitution, read-only modes, hardlinks and symlinks.
Successful structural mapping remains identity evidence, not behavioral completion.

The MCP whole-file receipt is stale after these changes. A fresh maintenance review and separate
human approval of its exact digest are required before receipt refresh. This addendum, QA
verdict, and permission to merge do not record that approval. The original requirement approval
and the other fresh receipts remain unchanged.
