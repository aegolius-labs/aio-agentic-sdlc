# Cross-Platform Agent Customization Research

**Timestamp:** 2026-06-22T13:08:13-04:00  
**Data Freshness:** Tech-related (requires refresh after 1 week)

As AI coding assistants and agents evolve, different platforms have adopted overlapping but distinct paradigms for customization. To build tooling that works across the entire "stack" (VS Code/GitHub Copilot, Copilot CLI, Claude Code, Cursor IDE, and Antigravity IDE), we must understand both the common standards and the proprietary mechanisms of each platform.

This living document tracks the paradigms across major platforms to inform architectural decisions for agent plugins and skills.

---

## 1. Custom Instructions & Behavioral Rules

**Purpose:** Defining "how to behave"—coding standards, architectural decisions, and project conventions (e.g., "always log features to the backlog").

| Platform | Standard/Implementation | Notes | Sources |
| :--- | :--- | :--- | :--- |
| **VS Code & GH Copilot** | `.github/copilot-instructions.md`<br>`AGENTS.md`<br>`*.instructions.md` | `AGENTS.md` is experimental but aimed at multiple agents. `*.instructions.md` supports glob-based scoping via YAML frontmatter. | [Copilot Docs](https://code.visualstudio.com/docs/agent-customization/overview), [GitHub Blog](https://github.blog/) |
| **Claude Code & CLI** | `CLAUDE.md` | Placed in the project root. Acts as the primary system prompt for project context. | [Claude Docs](https://docs.anthropic.com/en/docs/claude-code) |
| **Cursor IDE** | `.cursor/rules/*.mdc`<br>(Legacy: `.cursorrules`) | Modern `.mdc` files use YAML frontmatter to define `globs` and `description` to ensure rules only trigger when relevant to save context window tokens. | [Cursor Docs](https://docs.cursor.com/context/rules) |
| **Antigravity IDE** | `.agents/rules/`<br>Global Memory Files | Emphasizes automatic saving of session details and user global rules. | Internal System Rules |

**Cross-Platform Alignment:**
A single source of truth should be maintained for behavioral rules, which can then be compiled or injected into the platform-specific files (`CLAUDE.md`, `.cursor/rules/`, `AGENTS.md`) via an installation script to avoid drift.

---

## 2. Agent Skills

**Purpose:** Defining "how to do X"—multi-step workflows, scripts, and standard operating procedures loaded on demand.

| Platform | Standard/Implementation | Notes | Sources |
| :--- | :--- | :--- | :--- |
| **VS Code / Copilot / CLI** | `.github/skills/<name>/SKILL.md`<br>`.agents/skills/<name>/SKILL.md` | Based on the open `agentskills.io` standard. Uses YAML frontmatter (`name`, `description`). Called via slash commands. | [Copilot Skills](https://code.visualstudio.com/docs/agent-customization/overview) |
| **Claude Code** | `SKILL.md` inside plugins | Skills are reusable instruction packages invoked via slash commands or triggered autonomously. | [Claude Skills](https://docs.anthropic.com/en/docs/claude-code) |
| **Antigravity IDE** | `<plugin>/skills/<name>/SKILL.md` | Follows the same standard. Folders contain instructions, helper scripts, and examples. Agents read `SKILL.md` directly. | Internal Plugin Spec |

**Cross-Platform Alignment:**
The **Agent Skills Standard** (a folder containing a `SKILL.md` with YAML frontmatter) is the most universally adopted standard. Skills should *strictly* focus on technical execution and avoid behavioral dictates.

---

## 3. Custom Agents & Subagents

**Purpose:** Defining specific personas with restricted tool access, distinct models, and specialized instructions.

| Platform | Standard/Implementation | Notes | Sources |
| :--- | :--- | :--- | :--- |
| **VS Code / Copilot** | `.github/agents/*.agent.md`<br>`.claude/agents/*.md` | Uses YAML frontmatter to restrict `tools`, choose `model`, and define `handoffs` between agents sequentially. | [Copilot Agents](https://code.visualstudio.com/docs/agent-customization/overview) |
| **Claude Code** | Subagents | Spawns autonomous sub-processes with their own prompt and tools. Great for focused tasks (running tests) without polluting main context. | [Claude Subagents](https://docs.anthropic.com/en/docs/claude-code) |
| **Cursor IDE** | N/A (Handled via MDC rules) | Cursor primarily relies on deep context embedding rather than spawning distinct persona subagents. | [Cursor Rules](https://docs.cursor.com/) |

**Cross-Platform Alignment:**
Defining `.agent.md` files ensures that specialized personas can be triggered across the CLI and IDE.

---

## 4. Plugins & MCP (Model Context Protocol)

**Purpose:** Extending agent capabilities with external integrations, bundling skills, agents, and hooks into distributable packages.

| Platform | Standard/Implementation | Notes | Sources |
| :--- | :--- | :--- | :--- |
| **Model Context Protocol (MCP)** | `mcp.json` / Dynamic registration | The universal "USB-C" port for agents. Supported by Claude Code, VS Code, Cursor, Antigravity IDE, and Copilot CLI. | [MCP Spec](https://modelcontextprotocol.io/) |
| **VS Code / Copilot** | Agent Plugins (Preview) | Bundles instructions, skills, agents, and MCPs into a single installable package. | [Copilot Plugins](https://code.visualstudio.com/docs) |
| **Claude Code** | Plugin directories | Self-contained directories packaging skills, agents, hooks, and MCP servers. | [Claude Plugins](https://docs.anthropic.com/) |
| **Antigravity IDE** | `plugin.json` | Directory structure containing `plugin.json`, `/skills/`, and `/agents/`. | Internal Plugin Spec |

**Cross-Platform Alignment:**
MCP is the undisputed king of tool integration. Any tool logic should be exposed as an MCP server. The wrapper (Plugin) format differs slightly per platform, but the underlying skills and MCP servers remain identical.

---

## Synthesis & Implementation Strategy for `agentic-backlog`

To ensure `agentic-backlog` works optimally across all platforms, we should implement a **Single Source of Truth (SSoT) + Generator Pattern**:

1. **Behavioral Rules SSoT**: Maintain a single configuration file (e.g., `agentic_backlog_rules.md` or embedded in the python package) containing the behavioral instruction: "Do not assume immediate implementation. Log feature ideas to the backlog."
2. **Installation CLI**: Implement an initialization command (e.g., `agentic-backlog init`) that asks the user for their IDE stacks and automatically generates `CLAUDE.md`, `.cursor/rules/backlog.mdc`, or `AGENTS.md` injected with the SSoT rules.
3. **Technical Skill**: Keep `.agents/skills/agentic-backlog/SKILL.md` strictly focused on technical execution via MCP.
