"""`aio-sdlc init` never blocks an agent waiting on a prompt."""

import json
import subprocess
import sys

from aio_agentic_sdlc import cli
from aio_agentic_sdlc.workspace import CONFIG_FILE


def _config(root):
    return json.loads((root / CONFIG_FILE).read_text(encoding="utf-8"))


def _fail_on_prompt(*_args):
    raise AssertionError("init prompted")


class _Terminal:
    def isatty(self):
        return True


def _run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["aio-sdlc", "init", "--empty", *args])
    cli.main()


def test_flags_choose_hierarchy_and_validation_without_prompting(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdin", _Terminal())
    monkeypatch.setattr("builtins.input", _fail_on_prompt)

    _run(monkeypatch, "--hierarchy", "deep", "--validation", "strict")

    config = _config(tmp_path)
    assert config["core"]["validation_mode"] == "strict"
    assert config["hierarchy"]["1"] == ["Initiative"]
    assert config["hierarchy"]["7"] == ["SubTask"]


def test_yes_uses_defaults_even_on_a_terminal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdin", _Terminal())
    monkeypatch.setattr("builtins.input", _fail_on_prompt)

    _run(monkeypatch, "--yes")

    config = _config(tmp_path)
    assert config["core"]["validation_mode"] == "flex"
    assert config["hierarchy"] == {
        "1": ["Epic"],
        "2": ["Feature"],
        "3": ["Task", "Bug"],
    }


def test_init_with_an_open_non_terminal_stdin_does_not_wait(tmp_path):
    """An agent harness often holds stdin open as a pipe and never writes to it."""

    log = tmp_path / "init.log"
    project = tmp_path / "project"
    project.mkdir()
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [sys.executable, "-m", "aio_agentic_sdlc.cli", "init", "--empty"],
            cwd=project,
            stdin=subprocess.PIPE,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            returncode = process.wait(timeout=60)
        finally:
            if process.poll() is None:
                process.kill()
            process.stdin.close()

    text = log.read_text(encoding="utf-8")
    assert returncode == 0, text
    assert "Select" not in text
    assert "validation: flex" in text
    assert _config(project)["core"]["validation_mode"] == "flex"
