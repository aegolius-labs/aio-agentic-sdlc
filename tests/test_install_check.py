"""`dag-tool doctor` (HARDENING-AC1): an installation check that never writes."""

import json

from click.testing import CliRunner

from aio_agentic_sdlc import install_check
from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.install_check import run_doctor


def _check(report, name):
    return next(c for c in report["checks"] if c["name"] == name)


def _snapshot(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_doctor_passes_in_an_empty_directory_and_writes_nothing(tmp_path):
    report = run_doctor(tmp_path)

    assert report["passed"] is True, report
    mcp = _check(report, "MCP server")
    assert mcp["data"]["server"] == "aio-agentic-sdlc"
    assert "get_next_task" in mcp["data"]["tools"]
    assert _check(report, "project")["data"] == {"initialized": False}
    assert _snapshot(tmp_path) == []


def test_doctor_loads_an_initialized_project(tmp_path):
    (tmp_path / ".aio-agentic-sdlc").mkdir()
    runner = CliRunner()
    created = runner.invoke(
        cli,
        [
            "intent",
            "create-node",
            "--file",
            str(tmp_path / ".aio-agentic-sdlc" / "intention-dag.yaml"),
            "--node-id",
            "9a3c2a51-6a8e-4c39-9d43-0d6f2b6a4f10",
            "--name",
            "Token Check",
            "--type",
            "component",
            "--payload-file",
            str(_intent_file(tmp_path)),
        ],
    )
    assert created.exit_code == 0, created.output

    project = _check(run_doctor(tmp_path, mcp=False), "project")

    assert project["passed"] is True
    assert project["data"]["loaded"] == ["Intention DAG (1 nodes)"]


def test_a_broken_intention_dag_fails_the_project_check(tmp_path):
    workspace = tmp_path / ".aio-agentic-sdlc"
    workspace.mkdir()
    (workspace / "intention-dag.yaml").write_text(
        "metadata: {name: x, version: '1'}\nnodes:\n- {id: a}\n", encoding="utf-8"
    )

    result = CliRunner().invoke(
        cli, ["doctor", "--project", str(tmp_path), "--no-mcp", "--format", "json"]
    )

    assert result.exit_code == 1
    report = json.loads(result.output)
    project = _check(report, "project")
    assert project["passed"] is False
    assert "intention-dag.yaml" in project["detail"]
    assert "MCP server" not in {c["name"] for c in report["checks"]}


def test_a_missing_entry_point_fails_both_dependent_checks(tmp_path, monkeypatch):
    monkeypatch.setattr(install_check, "_entry_point", lambda name: None)

    report = run_doctor(tmp_path)

    assert report["passed"] is False
    assert _check(report, "entry points")["detail"].startswith("not found:")
    assert _check(report, "MCP server")["detail"] == (
        "aio-agentic-sdlc-mcp is not installed"
    )


def test_a_server_that_cannot_start_is_reported_not_raised(tmp_path, monkeypatch):
    monkeypatch.setattr(
        install_check, "_entry_point", lambda name: str(tmp_path / "missing")
    )

    mcp = install_check.check_mcp_server(tmp_path, timeout=10)

    assert mcp.passed is False
    assert mcp.detail.startswith("handshake failed:")


def _intent_file(tmp_path):
    path = tmp_path / "intent.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "provenance": [
                    {
                        "source_type": "human_statement",
                        "reference": "test",
                        "statement": "Check tokens.",
                    }
                ],
                "assumptions": [],
                "ambiguities": [],
                "confidence": 0.9,
                "acceptance_criteria": [
                    {
                        "id": "AC1",
                        "statement": "Tokens are checked.",
                        "required_evidence": ["test:tokens"],
                    }
                ],
                "revision_history": [
                    {
                        "revision": 1,
                        "recorded_at": "2026-11-09T00:00:00Z",
                        "actor": "test",
                        "generator_version": "test",
                        "summary": "Created.",
                    }
                ],
                "responsible_agent": "test",
                "generator_version": "test",
                "approval": {"state": "draft"},
            }
        ),
        encoding="utf-8",
    )
    return path
