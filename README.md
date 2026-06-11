# Agentic Backlog Manager

A deterministic, 3-Dimensional Impact/Effort/Dependency backlog manager designed for AI/Agentic workflows.

It replaces token-heavy LLM prioritization of Markdown files with a strict, deterministic JSON-based tracking system. It calculates recursive dependency scores, performs topological sorting to ensure prerequisites come first, and auto-generates human-readable Markdown exports.

## Licensing Note

This project is intended for **Personal / Non-Commercial Use Only**. When you publish this to GitHub, it is highly recommended to select a license like the **PolyForm Noncommercial License 1.0.0** or **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** from the GitHub license templates.

## Installation & Configuration

Because `agentic-backlog` is an agentic-first toolkit, the easiest way to install and integrate the MCP Server into your IDE (VS Code, Cursor, Windsurf, Claude Desktop) is by using `uvx` to fetch the server directly from GitHub. This requires **zero local installation**.

Add the following to your IDE's `mcp.json` or equivalent configuration file:

```json
"mcpServers": {
  "agentic-backlog": {
    "command": "uvx",
    "args": [
      "--from",
      "git+https://github.com/aegolius-labs/agentic-backlog-cli",
      "agentic-backlog-mcp"
    ]
  }
}
```

### CLI Fallback

If you need to interact with the backlog via the terminal (or need to `init` the project as a human), you can execute the CLI commands directly from GitHub:

```bash
uvx --from git+https://github.com/aegolius-labs/agentic-backlog-cli agentic-backlog init
uvx --from git+https://github.com/aegolius-labs/agentic-backlog-cli agentic-backlog add "my-feature" --impact 5 --effort 3 --category "Security"
uvx --from git+https://github.com/aegolius-labs/agentic-backlog-cli agentic-backlog prioritize
uvx --from git+https://github.com/aegolius-labs/agentic-backlog-cli agentic-backlog export
```

## Integrations (OpenSpec & Spec-Kit)

`agentic-backlog` natively integrates with **Open-Spec** and **Spec-Kit** frameworks. When you run `agentic-backlog init` inside a workspace utilizing these frameworks (e.g. detecting `tasks.md` or `specs/*.md` files), the CLI will automatically parse your Markdown checklists and seed them dynamically into the resulting JSON tracking structure.
