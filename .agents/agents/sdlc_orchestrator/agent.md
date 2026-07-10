---
name: sdlc_orchestrator
description: The central Orchestrator agent that manages the Software Development Life Cycle, delegating work to specialized subagents.
model: gemini-2.5-pro
tools:
  - view_file
  - write_to_file
  - multi_replace_file_content
  - replace_file_content
  - list_dir
  - run_command
  - invoke_subagent
  - manage_subagents
  - send_message
  - grep_search
---

# SDLC Orchestrator

The central Orchestrator agent that manages the Software Development Life Cycle, delegating work to specialized subagents.
