# Product Requirement Document (PRD)

## Feature
Add `--version` flag to the `aio-sdlc` CLI

## Summary
The goal of this feature is to allow users to quickly identify which version of the `aio-sdlc` framework they are currently running. By providing a `--version` flag on the CLI entrypoint, users and administrators can easily verify the active deployment or debug environment setup issues.

## User Stories
- As a user, I want to type `aio-sdlc --version` in my terminal so that I can see the currently installed version of the framework.
- As a developer/support engineer, I want users to easily output their framework version so that I can provide accurate troubleshooting assistance.

## Requirements
- **CLI Flag:** The entrypoint `aio-sdlc` MUST support a `-v` and `--version` argument.
- **Output:** When the flag is passed, the CLI MUST output the current framework version to standard output (e.g., `aio-sdlc version 1.2.3`) and immediately exit with a `0` exit code.
- **Dependency Integration:** The version string should ideally be sourced dynamically from the project's metadata (e.g., `pyproject.toml`, package version) to avoid hardcoding.

## Out of Scope
- Command-line help text refactoring (beyond adding the version flag description).
- Upgrading or self-updating functionality.

## Acceptance Criteria
1. Running `aio-sdlc --version` prints the version string.
2. Running `aio-sdlc -v` prints the version string.
3. The CLI exits cleanly (exit code 0) after printing the version without executing any other logic.
