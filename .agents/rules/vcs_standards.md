---
name: vcs-standards
description: Enforces strict Version Control System rules, including Conventional Commits and Branching.
---

# VCS & Workflow Standards

These rules are mandatory for all agents and subagents operating within the `aio-agentic-sdlc` framework.

1. **Branching Strategy (GitHub Flow)**: 
   - You MUST NOT work directly on `main` or `master`.
   - You MUST proactively create a new branch for any new scope of work.
   - You MUST adhere strictly to Conventional Branching (e.g., `feature/*`, `bugfix/*`, `chore/*`).

2. **Commit Standards**: 
   - You MUST commit frequently.
   - All commits MUST adhere strictly to the Conventional Commits specification (e.g., `feat: added intention schema`, `fix: resolved DAG loop`).
   - Automated semantic versioning and release workflows are driven by these commits. Precision is mandatory.

3. **Pull Requests**: 
   - Upon completion of a scope of work and passing all QA checks, you MUST push your branch and open a Pull Request against `main`.
