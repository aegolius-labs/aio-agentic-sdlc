# Safeguards

## Protected state

- Mutate DAG and backlog state only through MCP, CLI, or the Python API.
- Generate documents and promote specs with framework tools.
- Do not manually repair YAML, JSON, generated frontmatter, or graph edges.
- Serialize state-changing tool calls; never let parallel agents race on shared state.

## Blocking

Mark a task blocked only when implementation cannot satisfy the accepted spec without a product,
architecture, dependency, permission, or tooling decision. Record the concrete reason and the
smallest decision needed to resume. Test failures are feedback, not automatically blockers.

## Scope and authorization

- Read-only inspection and local validation are normal workflow steps.
- Ask before adding a material dependency, widening the accepted product scope, or performing an
  external write not already authorized.
- Do not commit, push, open a pull request, change issues, or publish artifacts merely because a
  legacy role prompt says to do so.

## Validation

- Use UV for Python commands.
- Run focused tests while iterating and the full relevant suite before delivery.
- Validate changed Markdown when Markdownlint is installed.
- Inspect the final diff for unrelated changes, secrets, runtime state, and scratch files.
