# Antigravity plugin

The plugin in `plugins/aio-agentic-sdlc/` serves Antigravity from the same
`skills/` body as Claude Code and Codex. Antigravity reads two files at the
plugin root:

- `plugin.json`: the plugin's name, display name and description. Antigravity
  discards undocumented top-level fields, so the manifest uses only documented
  ones and declares no version.
- `mcp_config.json`: the MCP server launch, identical to `.mcp.json`.

`tests/test_host_manifest_parity.py` keeps both in step with the other hosts.

## Install

```powershell
agy plugin install https://github.com/aegolius-labs/aio-agentic-sdlc
```

Installing from the git URL or a local checkout's root works because
Antigravity treats a top-level `plugins/` folder as a set of plugins and
installs each subdirectory. You can also install the directory itself:

```powershell
agy plugin install <checkout>\plugins\aio-agentic-sdlc
```

Install copies the files, so it does not follow later edits. To develop
against a live checkout, link Antigravity's plugin directory to
`plugins\aio-agentic-sdlc`, not to the repository root. The repository root
has no `plugin.json`, so a link to it loads nothing. Restart Antigravity after
adding a plugin directory, because it discovers them at startup.

## Validate

```powershell
agy plugin validate plugins\aio-agentic-sdlc
```

A healthy result lists `skills : 1 processed` and `mcpServers : 1 processed`.
`agy plugin validate` exits 0 even when it finds nothing, so read those lines
rather than relying on the exit code.
