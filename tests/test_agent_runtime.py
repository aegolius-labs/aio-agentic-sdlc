"""ROADMAP M6, RUNTIME-AC1: agent invocation sits behind a runtime adapter."""

import ast
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from aio_agentic_sdlc import agent_runtime
from aio_agentic_sdlc.agent_runtime import (
    AgentRuntimeError,
    AntigravityRuntime,
    CommandRuntime,
    resolve_runtime,
    run_agent,
)

SRC = Path(__file__).resolve().parents[1] / "src" / "aio_agentic_sdlc"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv(agent_runtime.RUNTIME_ENV, raising=False)
    monkeypatch.delenv(agent_runtime.COMMAND_ENV, raising=False)


def _workspace(tmp_path, config):
    workspace = tmp_path / ".aio-agentic-sdlc"
    workspace.mkdir()
    (workspace / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return str(tmp_path)


def test_runtime_imports_live_only_behind_the_adapter():
    """No module outside the adapter imports a vendor agent SDK at all."""

    allowed = {"agent_runtime.py", "antigravity_compat.py"}
    offenders = []
    for path in SRC.rglob("*.py"):
        if path.name in allowed:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(name.startswith("google.antigravity") for name in names):
                offenders.append(str(path.relative_to(SRC)))
    assert offenders == []


def test_google_antigravity_is_an_optional_extra():
    import tomllib

    project = tomllib.loads(
        (SRC.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    assert not any(d.startswith("google-antigravity") for d in project["dependencies"])
    assert project["optional-dependencies"]["antigravity"] == ["google-antigravity"]


def test_config_selects_the_command_runtime(tmp_path):
    root = _workspace(
        tmp_path, {"runtime": "command", "runtime_command": ["claude", "-p"]}
    )

    runtime = resolve_runtime(root)

    assert isinstance(runtime, CommandRuntime)
    assert runtime.argv == ["claude", "-p"]


def test_environment_overrides_config(tmp_path, monkeypatch):
    root = _workspace(tmp_path, {"runtime": "antigravity"})
    monkeypatch.setenv(agent_runtime.RUNTIME_ENV, "command")
    monkeypatch.setenv(agent_runtime.COMMAND_ENV, "codex exec -")

    runtime = resolve_runtime(root)

    assert isinstance(runtime, CommandRuntime)
    assert runtime.argv == ["codex", "exec", "-"]


def test_default_is_antigravity_only_when_its_sdk_is_installed(tmp_path):
    with patch.object(agent_runtime, "_antigravity_installed", return_value=True):
        assert isinstance(resolve_runtime(str(tmp_path)), AntigravityRuntime)
    with patch.object(agent_runtime, "_antigravity_installed", return_value=False):
        with pytest.raises(AgentRuntimeError, match="No agent runtime is configured"):
            resolve_runtime(str(tmp_path))


def test_unknown_runtime_and_missing_command_fail_clearly(tmp_path, monkeypatch):
    monkeypatch.setenv(agent_runtime.RUNTIME_ENV, "copilot")
    with pytest.raises(AgentRuntimeError, match="Supported: antigravity, command"):
        resolve_runtime(str(tmp_path))
    monkeypatch.setenv(agent_runtime.RUNTIME_ENV, "command")
    with pytest.raises(AgentRuntimeError, match="runtime_command"):
        resolve_runtime(str(tmp_path))


@pytest.mark.asyncio
async def test_command_runtime_sends_instructions_and_prompt_on_stdin(tmp_path):
    received = tmp_path / "stdin.txt"
    script = (
        "import sys, pathlib; "
        f"pathlib.Path({str(received)!r}).write_text(sys.stdin.read())"
    )

    await CommandRuntime([sys.executable, "-c", script]).run(
        "You are the sdlc_orchestrator.", "Execute this task: add a version command"
    )

    assert received.read_text() == (
        "You are the sdlc_orchestrator.\n\n"
        "Execute this task: add a version command\n"
    )


@pytest.mark.asyncio
async def test_command_runtime_failure_raises():
    with pytest.raises(AgentRuntimeError, match="exited with 3"):
        await CommandRuntime([sys.executable, "-c", "raise SystemExit(3)"]).run(
            "s", "p"
        )
    with pytest.raises(AgentRuntimeError, match="Could not start"):
        await CommandRuntime(["aio-sdlc-no-such-agent-cli"]).run("s", "p")


@pytest.mark.asyncio
async def test_antigravity_runtime_without_sdk_names_the_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "google.antigravity", None)
    with pytest.raises(AgentRuntimeError, match=r"aio-agentic-sdlc\[antigravity\]"):
        await AntigravityRuntime().run("s", "p")


@pytest.mark.asyncio
async def test_run_agent_dispatches_to_the_resolved_runtime(tmp_path):
    calls = []

    class Recorder:
        name = "recorder"

        async def run(self, system_instructions, prompt):
            calls.append((system_instructions, prompt))

    with patch.object(agent_runtime, "resolve_runtime", return_value=Recorder()):
        await run_agent("instructions", "prompt", project_path=str(tmp_path))

    assert calls == [("instructions", "prompt")]
