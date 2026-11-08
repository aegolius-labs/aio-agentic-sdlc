"""Runtime adapter boundary for agent invocation (ROADMAP M6).

The orchestrator loop and ``plan`` hand an agent two strings, system
instructions and a prompt, and wait for it to finish. Which runtime runs
the agent is configuration, not code: every runtime-specific import lives
behind :class:`AgentRuntime`, so a Claude Code or Codex user never needs
another vendor's SDK installed.

A runtime only executes work. It never decides that work is done: completion
still comes from the diff and the evidence ledger (ADR 0003).

Selection, first match wins:

1. ``AIO_SDLC_RUNTIME`` in the environment.
2. ``"runtime"`` in ``.aio-agentic-sdlc/config.json``.
3. ``antigravity`` when the optional ``google-antigravity`` SDK is installed.

Runtimes:

- ``antigravity``: the Google Antigravity SDK (``pip install
  'aio-agentic-sdlc[antigravity]'``).
- ``command``: any agent CLI. ``runtime_command`` in config.json (or
  ``AIO_SDLC_RUNTIME_COMMAND``, a shell-style string) is the argv. The prompt,
  preceded by the system instructions, is written to the command's stdin, so
  ``["claude", "-p"]`` or ``["codex", "exec", "-"]`` work unchanged.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import shlex
from typing import Protocol, Sequence

RUNTIME_ENV = "AIO_SDLC_RUNTIME"
COMMAND_ENV = "AIO_SDLC_RUNTIME_COMMAND"
ANTIGRAVITY = "antigravity"
COMMAND = "command"
RUNTIMES = (ANTIGRAVITY, COMMAND)


class AgentRuntimeError(RuntimeError):
    """Raised when no runtime is configured or the selected one fails."""


class AgentRuntime(Protocol):
    """The stable contract every runtime implements."""

    name: str

    async def run(self, system_instructions: str, prompt: str) -> None:
        """Run one agent turn to completion; raise on failure."""


class AntigravityRuntime:
    """Google Antigravity SDK, imported only when this runtime is used."""

    name = ANTIGRAVITY

    async def run(self, system_instructions: str, prompt: str) -> None:
        try:
            from google.antigravity import Agent

            from aio_agentic_sdlc.antigravity_compat import local_agent_config
        except ImportError as exc:
            raise AgentRuntimeError(
                "The antigravity runtime needs the optional SDK: "
                "pip install 'aio-agentic-sdlc[antigravity]'."
            ) from exc
        async with Agent(local_agent_config(system_instructions)) as agent:
            await agent.chat(prompt)


class CommandRuntime:
    """Run an agent CLI with the prompt on stdin."""

    name = COMMAND

    def __init__(self, argv: Sequence[str]):
        if not argv or not all(isinstance(part, str) and part for part in argv):
            raise AgentRuntimeError(
                "The command runtime needs runtime_command: a non-empty list of "
                'strings, for example ["claude", "-p"].'
            )
        self.argv = list(argv)

    @staticmethod
    def compose(system_instructions: str, prompt: str) -> str:
        return f"{system_instructions.strip()}\n\n{prompt.strip()}\n"

    async def run(self, system_instructions: str, prompt: str) -> None:
        try:
            process = await asyncio.create_subprocess_exec(
                *self.argv,
                stdin=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise AgentRuntimeError(
                f"Could not start runtime command {self.argv[0]!r}: {exc}"
            ) from exc
        await process.communicate(
            self.compose(system_instructions, prompt).encode("utf-8")
        )
        if process.returncode != 0:
            raise AgentRuntimeError(
                f"Runtime command {self.argv[0]!r} exited with {process.returncode}."
            )


def _config(project_path: str) -> dict:
    from aio_agentic_sdlc.config import load_config

    try:
        config = load_config(project_path)
    except Exception:  # an absent or legacy workspace has no runtime setting
        return {}
    return config if isinstance(config, dict) else {}


def _antigravity_installed() -> bool:
    try:
        return importlib.util.find_spec("google.antigravity") is not None
    except ModuleNotFoundError:
        return False


def resolve_runtime(project_path: str = ".") -> AgentRuntime:
    """Return the configured runtime, or explain how to configure one."""

    config = _config(project_path)
    name = os.environ.get(RUNTIME_ENV) or config.get("runtime")
    if not name:
        if not _antigravity_installed():
            raise AgentRuntimeError(
                'No agent runtime is configured. Set "runtime" in '
                '.aio-agentic-sdlc/config.json to "command" with '
                '"runtime_command" (for example ["claude", "-p"]), or '
                "install 'aio-agentic-sdlc[antigravity]'."
            )
        name = ANTIGRAVITY
    if name == ANTIGRAVITY:
        return AntigravityRuntime()
    if name == COMMAND:
        command = os.environ.get(COMMAND_ENV)
        argv = shlex.split(command) if command else config.get("runtime_command")
        return CommandRuntime(argv or [])
    raise AgentRuntimeError(
        f"Unknown agent runtime {name!r}. Supported: {', '.join(RUNTIMES)}."
    )


async def run_agent(
    system_instructions: str, prompt: str, *, project_path: str = "."
) -> None:
    """Run one agent turn on the configured runtime."""

    await resolve_runtime(project_path).run(system_instructions, prompt)
