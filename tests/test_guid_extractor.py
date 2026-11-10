"""The Canonical GUID Extractor reads markers from comments and agent frontmatter."""

import json

from click.testing import CliRunner

from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.guid_extractor import (
    extract_comment_markers,
    extract_frontmatter_markers,
    scan_project,
)

KNOWN = "2e8a1562-7e77-4402-992f-f461e8c7161f"
OTHER = "9865715b-99a5-4dcb-ba92-90b03cc3cf1c"


def _write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _intention(root, *ids):
    nodes = "".join(
        f"- id: {node_id}\n  type: component\n  name: N{index}\n"
        for index, node_id in enumerate(ids)
    )
    _write(
        root,
        ".aio-agentic-sdlc/intention-dag.yaml",
        f"metadata:\n  name: test\nnodes:\n{nodes}edges: []\n",
    )


def test_comment_markers_come_from_comments_only():
    source = (
        f"# aio-sdlc-node: {KNOWN}\n"
        "class A:\n"
        f'    """# aio-sdlc-node: {OTHER}"""\n'
        f'    value = "# aio-sdlc-node: {OTHER}"\n'
    ).encode()

    markers, malformed = extract_comment_markers(source, "a.py")

    assert [(m.guid, m.line, m.source) for m in markers] == [(KNOWN, 1, "comment")]
    assert malformed == []


def test_a_comment_marker_that_is_not_a_uuid_is_malformed():
    markers, malformed = extract_comment_markers(
        b"# aio-sdlc-node: not-a-uuid\nx = 1\n", "a.py"
    )

    assert markers == []
    assert [(m.line, m.text) for m in malformed] == [(1, "# aio-sdlc-node: not-a-uuid")]


def test_frontmatter_yields_metadata_node_id_and_marker_key():
    text = (
        "---\n"
        "name: sdlc_qa\n"
        f"aio-sdlc-node: {KNOWN.upper()}\n"
        "metadata:\n"
        f"  node_id: {OTHER}\n"
        "---\n"
        "body\n"
    )

    markers, malformed = extract_frontmatter_markers(text, "agent.md")

    assert sorted((m.guid, m.line) for m in markers) == [(KNOWN, 3), (OTHER, 5)]
    assert {m.source for m in markers} == {"frontmatter"}
    assert malformed == []


def test_frontmatter_without_a_marker_or_closing_fence_yields_nothing():
    assert extract_frontmatter_markers("---\nname: a\n---\n", "a.md") == ([], [])
    assert extract_frontmatter_markers(f"---\nnode_id: {KNOWN}\n", "a.md") == (
        [],
        [],
    )
    assert extract_frontmatter_markers("no frontmatter", "a.md") == ([], [])


def test_frontmatter_problems_are_malformed():
    _, bad_value = extract_frontmatter_markers(
        "---\nmetadata:\n  node_id: 42\n---\n", "a.md"
    )
    _, bad_yaml = extract_frontmatter_markers("---\nname: [\n---\n", "a.md")

    assert [(m.line, m.text) for m in bad_value] == [(3, "node_id: 42")]
    assert [m.text for m in bad_yaml] == ["invalid YAML"]


def test_a_clean_project_passes(tmp_path):
    _intention(tmp_path, KNOWN, OTHER)
    _write(tmp_path, "src/a.py", f"# aio-sdlc-node: {KNOWN}\ndef a():\n    pass\n")
    _write(
        tmp_path,
        ".agents/agents/qa.md",
        f"---\nname: qa\nmetadata:\n  node_id: {OTHER}\n---\n",
    )

    report = scan_project(tmp_path)

    assert report["passed"] is True
    assert sorted((m["path"], m["guid"]) for m in report["markers"]) == [
        (".agents/agents/qa.md", OTHER),
        ("src/a.py", KNOWN),
    ]


def test_scan_skips_tests_ignored_dirs_and_non_agent_markdown(tmp_path):
    _intention(tmp_path, KNOWN)
    marker = f"# aio-sdlc-node: {OTHER}\nx = 1\n"
    _write(tmp_path, "tests/test_a.py", marker)
    _write(tmp_path, ".venv/lib/a.py", marker)
    _write(tmp_path, "docs/page.md", f"---\naio-sdlc-node: {OTHER}\n---\n")

    report = scan_project(tmp_path)

    assert report["markers"] == []
    assert report["passed"] is True


def test_scan_reports_duplicates_unknown_and_malformed(tmp_path):
    _intention(tmp_path, KNOWN)
    _write(tmp_path, "src/a.py", f"# aio-sdlc-node: {KNOWN}\nx = 1\n")
    _write(tmp_path, "src/b.py", f"# aio-sdlc-node: {KNOWN}\ny = 1\n")
    _write(tmp_path, "src/c.py", f"# aio-sdlc-node: {OTHER}\nz = 1\n")
    _write(tmp_path, "src/d.py", "# aio-sdlc-node: nope\n")

    report = scan_project(tmp_path)

    assert report["passed"] is False
    assert report["duplicates"] == {KNOWN: ["src/a.py:1", "src/b.py:1"]}
    assert [m["guid"] for m in report["unknown"]] == [OTHER]
    assert [m["path"] for m in report["malformed"]] == ["src/d.py"]


def test_without_an_intention_dag_unknown_is_not_checked(tmp_path):
    _write(tmp_path, "src/a.py", f"# aio-sdlc-node: {OTHER}\nx = 1\n")

    report = scan_project(tmp_path)

    assert report["intention_dag"] is False
    assert report["unknown"] == []
    assert report["passed"] is True


def test_cli_reports_and_exits_on_problems(tmp_path):
    _intention(tmp_path, KNOWN)
    _write(tmp_path, "src/a.py", f"# aio-sdlc-node: {OTHER}\nx = 1\n")
    runner = CliRunner()

    text = runner.invoke(cli, ["guids", "--project-path", str(tmp_path)])
    data = runner.invoke(
        cli, ["guids", "--project-path", str(tmp_path), "--format", "json"]
    )

    assert text.exit_code == 1
    assert f"{OTHER} at src/a.py:1 is not an Intention DAG node" in text.output
    assert json.loads(data.output)["unknown"][0]["guid"] == OTHER


def test_this_repository_has_no_marker_problems():
    report = scan_project(".")

    assert report["passed"] is True, report
    assert report["markers"]
