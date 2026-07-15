# Agentic Backlog Manager

A deterministic, 3-Dimensional Impact/Effort/Dependency backlog manager designed for AI/Agentic workflows.

It replaces token-heavy LLM prioritization of Markdown files with a strict, deterministic JSON-based tracking system. It calculates recursive dependency scores, performs topological sorting to ensure prerequisites come first, and auto-generates human-readable Markdown exports.

## Architectural Highlights

The `aio-agentic-sdlc` framework includes several built-in features that ensure deterministic, secure, and traceable agentic operations:

- **Canonical GUID Traceability**: Node IDs map natively and consistently across your PRDs, codebase comments, and DAG structures.
- **QA Sandbox Isolation**: QA agents operate strictly within robust `.qa-sandbox/<session-id>/` environments to ensure they cannot leak or destructively modify core source files.
- **MCP Server Integration**: Downstream subagents securely interact with the system via integrated MCP servers, most notably the Agentic Backlog server.
- **SDLC Scribe Agent**: An automated Scribe agent executes before the DevOps agent steps to ensure user-facing documentation (like this README) stays perfectly aligned with the codebase's true reality.

## Licensing Note

This project is intended for **Personal / Non-Commercial Use Only**. When you publish this to GitHub, it is highly recommended to select a license like the **PolyForm Noncommercial License 1.0.0** or **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** from the GitHub license templates.

## Installation & Configuration

Because `aio-agentic-sdlc` is an agentic-first toolkit, the easiest way to install and integrate the MCP Server into your IDE (VS Code, Cursor, Windsurf, Claude Desktop) is by using `uvx` to fetch the server directly from GitHub. This requires **zero local installation**.

Add the following to your IDE's `mcp.json` or equivalent configuration file:

```json
"mcpServers": {
  "aio-agentic-sdlc": {
    "command": "uvx",
    "args": [
      "--from",
      "git+https://github.com/aegolius-labs/aio-agentic-sdlc-cli",
      "aio-agentic-sdlc-mcp"
    ]
  }
}
```

### Global Installation (Optional)

If you plan to use the CLI frequently and prefer not to type the full `uvx` GitHub URL every time, you can permanently install the CLI globally using `uv`:

```bash
uv tool install git+https://github.com/aegolius-labs/aio-agentic-sdlc-cli
```

Once installed, you can invoke the CLI natively:

```bash
agb init
agb add "my-feature" --impact 5 --effort 3 --category "Security"
agb prioritize
agb export
```

*(Note: `aio-agentic-sdlc` can also be used if you prefer the full name)*

### Zero-Install Execution (via uvx)

If you prefer not to install the CLI globally, you can execute commands entirely on-the-fly directly from GitHub:

```bash
uvx --from git+https://github.com/aegolius-labs/aio-agentic-sdlc-cli agb init
uvx --from git+https://github.com/aegolius-labs/aio-agentic-sdlc-cli agb export
```

## Spec-Driven Development (SDD)

`aio-agentic-sdlc` utilizes its own Spec-Driven Development (SDD) framework to bridge the gap between high-level architectural planning and deterministic code execution.

Instead of relying on token-heavy LLM context windows or external integrations, the framework strictly enforces:

- **Intention DAG (I-DAG)**: A graph-based structural representation of planned features and dependencies.
- **Reality DAG (R-DAG)**: A deterministic reflection of the actual codebase logic.
- **Canonical Traceability**: PRDs (Product Requirement Documents) in the `specs/` directory are firmly anchored to both DAGs using `aio-sdlc-node` GUID tags, allowing subagents to detect architectural drift automatically and execute Just-In-Time (JIT) TDD loops with zero hallucination.
