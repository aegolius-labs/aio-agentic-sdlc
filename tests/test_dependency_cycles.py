"""A write that would close a dependency cycle is rejected before it lands."""

import json

import pytest

from aio_agentic_sdlc.cli import load_backlog, save_backlog
from aio_agentic_sdlc.core import add_item, prioritize_items, update_item
from aio_agentic_sdlc.state import DependencyCycleError, find_requires_cycle


@pytest.fixture(autouse=True)
def clean_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_backlog({})


def _add(name, requires=None):
    add_item(name, 3, 3, "core", description=f"{name} work", requires=requires)


def _requires():
    edges = load_backlog().get("edges", [])
    return sorted((e["from"], e["to"]) for e in edges if e["relation"] == "requires")


def _item(name):
    return {
        "impact": 3,
        "effort": 3,
        "category": "core",
        "description": f"{name} work",
        "status": "New",
        "blockers": [],
        "scores": {},
    }


def test_add_rejects_self_dependency():
    with pytest.raises(DependencyCycleError, match="D -> D"):
        _add("D", requires="D")
    assert "D" not in load_backlog()["nodes"]


def test_update_rejects_dependency_that_closes_a_cycle():
    _add("A")
    _add("B", requires="A")
    _add("C", requires="B")
    before = load_backlog()

    with pytest.raises(DependencyCycleError, match="A -> C -> B -> A"):
        update_item("A", requires="C")

    assert load_backlog() == before


def test_direct_saves_cannot_introduce_a_cycle():
    """ingest_diff and migration write through save_backlog, not add/update."""

    data = load_backlog()
    data["nodes"] = {"X": _item("X"), "Y": _item("Y")}
    data["edges"] = [
        {"from": "X", "to": "Y", "relation": "requires"},
        {"from": "Y", "to": "X", "relation": "requires"},
    ]
    with pytest.raises(DependencyCycleError):
        save_backlog(data, operation="backlog.ingest-diff")
    assert load_backlog()["nodes"] == {}


def test_an_already_cyclic_backlog_can_still_be_repaired(tmp_path):
    _add("A")
    _add("B", requires="A")
    path = tmp_path / ".aio-agentic-sdlc" / "backlog.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["edges"].append({"from": "A", "to": "B", "relation": "requires"})
    path.write_text(json.dumps(raw), encoding="utf-8")

    update_item("A", impact=4)
    update_item("A", requires="")
    assert _requires() == [("B", "A")]


def test_long_chains_do_not_hit_the_recursion_limit():
    count = 3000
    nodes = {f"n{i}": {} for i in range(count)}
    edges = [
        {"from": f"n{i}", "to": f"n{i + 1}", "relation": "requires"}
        for i in range(count - 1)
    ]
    assert find_requires_cycle(nodes, edges) is None
    edges.append({"from": f"n{count - 1}", "to": "n0", "relation": "requires"})
    cycle = find_requires_cycle(nodes, edges)
    assert cycle[0] == cycle[-1] and len(cycle) == count + 1

    data = load_backlog()
    data["nodes"] = {name: _item(name) for name in nodes}
    data["edges"] = edges[:-1]
    save_backlog(data)
    prioritize_items()


def test_acyclic_dependencies_are_still_accepted():
    _add("A")
    _add("B", requires="A")
    _add("C", requires="A,B")
    update_item("A", requires="")
    assert _requires() == [("B", "A"), ("C", "A"), ("C", "B")]


def test_missing_dependency_is_still_created_as_placeholder():
    warnings = add_item("A", 3, 3, "core", description="A work", requires="Later")
    assert any("Later" in warning for warning in warnings)
    assert "Later" in load_backlog()["nodes"]
