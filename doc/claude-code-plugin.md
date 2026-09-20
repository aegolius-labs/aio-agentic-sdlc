# Claude Code and Claude Desktop

The framework exposes its deterministic surface as an MCP server over stdio, so any
MCP-capable Claude client can drive it. There are three ways in, from least to most
integrated.

## 1. Open the repository in Claude Code

Claude Code auto-discovers `.mcp.json` at the project root. Opening this repository is
enough — the 23 tools, 2 resources, and 1 prompt register automatically. Nothing to
install.

This does **not** load the `manage-sdlc` skill. You get the tools; you do not get the
workflow guidance that tells an agent which role to read and in what order.

## 2. Install the plugin

Gets both the tools and the skill.

```powershell
claude plugin marketplace add ./aio-agentic-sdlc
claude plugin install aio-agentic-sdlc@aegolius-labs-sdlc
```

The marketplace at `.claude-plugin/marketplace.json` points at
`plugins/aio-agentic-sdlc/`, the same directory the Codex marketplace uses. Both hosts
load the same `skills/manage-sdlc/` body and the same `.mcp.json`; only the manifest
differs. `tests/test_host_manifest_parity.py` fails if they drift.

## 3. Claude Desktop

Claude Desktop's chat surface does not read `.mcp.json`. Add the server to
`claude_desktop_config.json`:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "aio-agentic-sdlc": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/aegolius-labs/aio-agentic-sdlc",
        "aio-agentic-sdlc-mcp"
      ]
    }
  }
}
```

Restart the app afterwards. The Claude Code tab inside the desktop app uses the Claude
Code mechanisms above instead, so options 1 and 2 already cover it.

## Working from a local checkout

The shipped configuration launches through `uvx --from git+...`, which is correct for
installed users but fetches from GitHub. To drive the code you are editing, point the
server at the local project instead:

```json
{
  "mcpServers": {
    "aio-agentic-sdlc-local": {
      "command": "uv",
      "args": ["run", "--no-sync", "aio-agentic-sdlc-mcp"],
      "cwd": "X:\\absolute\\path\\to\\aio-agentic-sdlc"
    }
  }
}
```

Use a distinct server name as shown. Two servers registered under the same name — for
example the installed plugin plus a local override — collide.

## Verifying the connection

The server identifies itself as `aio-agentic-sdlc` with the installed distribution
version. A healthy handshake reports protocol `2025-11-25`, 23 tools, 2 resources, and
1 prompt. Running from a source tree with no installed distribution metadata reports
version `0.0.0+unknown`, which is expected rather than an error.

Ask Claude to call `get_next_task`. On a project with no backlog it returns
`Warning: Backlog is empty.`, which confirms the round trip.

## What the tools will and will not do

The MCP surface is deterministic state and artifact manipulation. It does not relax the
authority model:

- Backlog mutations operate on the derived layer 3 queue, never on layer 1 intent.
- `set_intent` and `create_intent_node` are the only intent mutation surfaces, and they
  require an expected revision.
- `review_mapping` is read-only. `approve_mapping` requires an evidence digest produced
  by that review, and the approval means only that a source symbol is the canonical
  implementation identity for a node.

See `CLAUDE.md` for the model an agent needs before using any of this, and
`doc/authority-model.md` for the normative statement.
