# Installation and release contract

This page states what an adopter can rely on across releases, and how to check
that an installation works. It covers Product Hardening's HARDENING-AC1.

## Install

The package needs Python 3.11 or later.

```bash
uv tool install git+https://github.com/aegolius-labs/aio-agentic-sdlc
# or, in a project environment
uv pip install git+https://github.com/aegolius-labs/aio-agentic-sdlc
```

The `semantic` extra adds duplicate-PRD detection, and it pulls in PyTorch.
The `antigravity` extra adds the Antigravity agent runtime. Neither is needed
for the CLI, the MCP server, the closed-loop demo or the benchmark.

## Check the installation

```bash
dag-tool doctor
```

`doctor` is read-only. It checks four things and exits 1 if any fails:

| Check | Passes when |
| --- | --- |
| package | always; reports the installed version and Python |
| entry points | `aio-sdlc`, `dag-tool` and `aio-agentic-sdlc-mcp` are installed |
| MCP server | the installed server completes a real stdio handshake as `aio-agentic-sdlc` and lists its tools |
| project | the current directory has no `.aio-agentic-sdlc/`, or every state file in it loads and validates |

Use `--format json` for scripts, `--no-mcp` to skip starting the server, and
`--project <dir>` to check another directory. CI runs `doctor` from the
installed wheel alone and requires the 24 MCP tools.

To see the whole loop work after that, run `dag-tool demo --directory <empty dir>
--approver "<your name>"` (see the README).

## Host plugins

| Host | Install | Updates |
| --- | --- | --- |
| Claude Code | `claude plugin marketplace add aegolius-labs/aio-agentic-sdlc`, then `claude plugin install aio-agentic-sdlc@aegolius-labs-sdlc` | By commit: `claude plugin update aio-agentic-sdlc@aegolius-labs-sdlc` delivers the latest skill |
| Codex | see `doc/codex-plugin.md` | The manifest names the latest release |
| Antigravity | see `doc/antigravity-plugin.md` | From the git URL |

The Claude Code manifests declare no version on purpose. Claude Code treats a
declared version as a cache key, so a number that stays the same blocks every
update. CI validates the Claude Code manifests and skills with Claude Code's
bundled validator, then installs the plugin from the checkout into an empty
profile. CI does not install the Codex or Antigravity plugins, because neither
host offers a validator that can run there. `tests/test_host_manifest_parity.py`
keeps all three manifests consistent.

Every host plugin starts the MCP server with `uvx --from
git+https://github.com/aegolius-labs/aio-agentic-sdlc aio-agentic-sdlc-mcp`, so
the first start downloads the package.

## What is stable

The project is pre-1.0. A release may still break any of the following, but it
must name the break in its pull request and in `CHANGELOG.md`:

- **Entry points**: `aio-sdlc` (also `aio-agentic-sdlc` and `agb`), `dag-tool`,
  `aio-agentic-sdlc-mcp`.
- **MCP surface**: the 24 tool names listed in `CLAUDE.md`, the
  `backlog://current` and `backlog://hierarchy-rules` resources, and stdio
  transport. `tests/test_mcp_v2_contract.py` pins both sets.
- **State files**: the committed `intention-dag.yaml`, `reality-dag.yaml` and
  `evidence.json`, plus the gitignored `backlog.json`. Intent IR is
  `schema_version` 1 (ADR 0002). The backlog envelope carries its own
  `schema_version` (ADR 0001); a newer schema fails closed and is never
  downgraded.
- **Federation seams**: `seam-a-work` v1 out to agentic-backlog-kit and
  `abk-observed-state` v1 back (see `doc/authority-model.md`). Additive fields
  keep the version. Removals and renames bump it.

Releases come from Conventional Commits merged to `main`. `feat:` cuts a minor
version, `fix:` a patch, and `docs:` or `chore:` cuts none. Each release is a
git tag and a GitHub Release.

When something fails after installation, see `doc/recovery.md`.
