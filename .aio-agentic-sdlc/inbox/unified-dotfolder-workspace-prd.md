# PRD: Unified Dotfolder Workspace Structure

## Background
Currently, the aio-agentic-sdlc framework scatters its operational directories and files (`inbox/`, `specs/`, `changes/`, `archive/`, `research-spikes/`, `intention-dag.yaml`, `reality-dag.yaml`, `backlog.json`) directly into the root of the user's workspace. This pollutes the root directory of the codebase where the framework is installed.

## Requirements
1. **Common Root Directory**: All framework-specific files and operational folders must be moved under a single root directory named `.aio-agentic-sdlc/`.
   - `.aio-agentic-sdlc/inbox/`
   - `.aio-agentic-sdlc/specs/`
   - `.aio-agentic-sdlc/changes/`
   - `.aio-agentic-sdlc/archive/`
   - `.aio-agentic-sdlc/research-spikes/`
   - `.aio-agentic-sdlc/intention-dag.yaml`
   - `.aio-agentic-sdlc/reality-dag.yaml`
   - `.aio-agentic-sdlc/backlog.json`
2. **Eager Bootstrapping**: The CLI initialization/bootstrapping command (e.g., `agb init` or similar framework initialization) must be updated. Upon bootstrapping, the `.aio-agentic-sdlc/` folder and all its required subdirectories should be eagerly created.
3. **Configuration Updates**: All Python source code (`src/aio_agentic_sdlc/config.py`, `core.py`, `cli.py`, etc.) must be updated to read and write from this new common root folder.
4. **Agent Instruction Updates**: The markdown files for the SDLC agents in `.agents/agents/` must have their prompts updated to reflect the new paths (e.g. changing `inbox/` to `.aio-agentic-sdlc/inbox/`). Note: The `.agents/` folder itself is managed by Antigravity and should remain at the workspace root, but the agents' internal text prompts need updating to point to the new framework paths.

## Acceptance Criteria
- Running the init command creates the full `.aio-agentic-sdlc/` tree.
- `uv run pytest` passes (unit tests updated to mock/use the new paths).
- The orchestrator loop correctly ingests PRDs from `.aio-agentic-sdlc/inbox/`.
