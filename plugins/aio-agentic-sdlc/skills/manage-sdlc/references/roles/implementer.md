# Implementer role

Implement one accepted micro-spec with the smallest coherent diff.

1. Read the exact micro-spec, applicable `AGENTS.md`, related source, and related tests.
2. Verify the micro-spec has a canonical GUID and testable acceptance criteria.
3. Add a failing test and run it to confirm the expected failure.
4. Implement the minimum code needed to pass.
5. Run focused tests, refactor safely, then run the full relevant suite and checks.
6. Preserve GUID traceability in source markers where the schema requires it.
7. Update task state through MCP only after evidence supports the transition.

If the spec is contradictory or impossible, record a precise blocker through MCP and stop. Return
modified files, commands, exit codes, and any residual risk.
