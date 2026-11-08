"""Version Command: report the framework version safely before initialization."""

import subprocess
import sys
from importlib import metadata

import pytest
from click.testing import CliRunner

import aio_agentic_sdlc
from aio_agentic_sdlc import cli as backlog_cli
from aio_agentic_sdlc import mcp_server
from aio_agentic_sdlc.dag_cli import cli as dag_cli


def test_package_version_is_the_installed_distribution():
    assert aio_agentic_sdlc.__version__ == metadata.version("aio-agentic-sdlc")


def test_backlog_cli_reports_version_without_a_workspace(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["aio-sdlc", "--version"])

    with pytest.raises(SystemExit) as exited:
        backlog_cli.main()

    assert exited.value.code == 0
    assert capsys.readouterr().out.strip() == (
        f"aio-sdlc {aio_agentic_sdlc.__version__}"
    )
    assert list(tmp_path.iterdir()) == []


def test_dag_tool_reports_version_without_a_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(dag_cli, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == f"dag-tool, version {aio_agentic_sdlc.__version__}"
    assert list(tmp_path.iterdir()) == []


def test_mcp_server_advertises_the_same_version():
    assert mcp_server._server_version() == aio_agentic_sdlc.__version__


def test_installed_entrypoint_reports_version(tmp_path):
    completed = subprocess.run(
        [sys.executable, "-m", "aio_agentic_sdlc.cli", "--version"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert aio_agentic_sdlc.__version__ in completed.stdout
