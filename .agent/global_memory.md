# Global AI Memory & Lessons Learned

## Workflow & Git Constraints

- **Branching:** MUST create a new branch (`feature/*`, `chore/*`, `hotfix/*`) for ANY new scope of work. MUST NOT commit directly to `dev` or `main`.
- **Committing:** MUST commit frequently using Conventional Commits.
- **Internal Directives vs Distribution Rules:** Directives meant specifically for the agent working on the repository itself (e.g., "document errors you encounter while developing") MUST NOT be added to templates distributed to end-users (`RULES.md`, `SKILL.md`, `AGENTS.md`). Template rules apply only to the end-user's execution environment.
- **GitHub MCP EOF Failure Fallback:** If `github-mcp-server` tools (e.g. `search_issues`) fail with an EOF connection closed error, you must aggressively fallback to alternate means, such as writing a temporary Python script utilizing the local repository's `GitHubClient` module.

## Tools & API Interactions

- **Tool Fallbacks:** If an MCP tool (like `github-mcp-server`) fails due to auth or permissions (e.g. 403), MUST fallback to the corresponding CLI tool (e.g. `gh issue create`) before giving up, respecting the Tool Preference hierarchy (MCP > CLI > API).
- **PowerShell Encoding:** NEVER use `echo "text" >> file` in Windows PowerShell. It defaults to UTF-16LE and corrupts UTF-8 files. MUST use explicit file tools (`replace_file_content` or `write_to_file`).
- **Python Versioning:** Since the project is UV-first, always default to upgrading to more recent versions of Python if a dependency or architecture requires it. Do not block or ask for permission for minor version bumps.
- **IDE Knowledge:** VS Code natively supports a global `mcp.json` file as of v1.121.0+. Do not assume only AI-first forks (Cursor/Windsurf) use MCP configuration files.
- **Agy IDE MCP Config:** Agy IDE (Antigravity) does NOT read MCP servers from `settings.json` or `mcp.json`. It strictly uses `%USERPROFILE%\.gemini\config\mcp_config.json`. Furthermore, each MCP server entry MUST include the attribute `"$typeName": "exa.cascade_plugins_pb.CascadePluginCommandTemplate"` to load successfully.
- **MCP State Inconsistency:** If an MCP server returns unexpected empty data (e.g., `agentic-backlog` returning an empty backlog), fallback to the native CLI equivalent (e.g., `uvx agentic-backlog next`), as the CLI may have correct access to local state files.
- **GitHub CLI Organization Permissions:** If `gh repo create` fails with `GraphQL: Resource not accessible by personal access token`, the authenticated token lacks OAuth scopes for repository creation in that specific Organization (or requires SAML SSO authorization). The user must be instructed to create the repository manually via the web UI or update their token scopes using `gh auth refresh -s repo`.
- **GitHub Actions Reusable Workflows:** When a caller workflow references a reusable workflow located in the *same* repository, you MUST use the relative path syntax (e.g., `uses: ./.github/workflows/reusable.yml`) without a branch ref (`@main`). Using the absolute `owner/repo/.github/...@main` syntax causes a `startup_failure`.
