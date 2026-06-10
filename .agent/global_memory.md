# Global AI Memory & Lessons Learned

## Workflow & Git Constraints

- **Branching:** MUST create a new branch (`feature/*`, `chore/*`, `hotfix/*`) for ANY new scope of work. MUST NOT commit directly to `dev` or `main`.
- **Committing:** MUST commit frequently using Conventional Commits.

## Tools & API Interactions

- **Tool Fallbacks:** If an MCP tool (like `github-mcp-server`) fails due to auth or permissions (e.g. 403), MUST fallback to the corresponding CLI tool (e.g. `gh issue create`) before giving up, respecting the Tool Preference hierarchy (MCP > CLI > API).
- **PowerShell Encoding:** NEVER use `echo "text" >> file` in Windows PowerShell. It defaults to UTF-16LE and corrupts UTF-8 files. MUST use explicit file tools (`replace_file_content` or `write_to_file`).
