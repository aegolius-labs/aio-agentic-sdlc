"""update_item validates a type or parent change like add_item does."""

import pytest

from aio_agentic_sdlc.cli import load_backlog, save_backlog
from aio_agentic_sdlc.core import BacklogOperationError, add_item, update_item


@pytest.fixture(autouse=True)
def clean_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_backlog({})


def _add(name, item_type, parent_id=None):
    add_item(
        name,
        3,
        3,
        "core",
        description=f"{name} work",
        item_type=item_type,
        parent_id=parent_id,
    )


def _parent(name):
    for edge in load_backlog().get("edges", []):
        if edge["from"] == name and edge["relation"] == "parent":
            return edge["to"]
    return None


def test_rejects_reparenting_under_a_lower_level():
    _add("E", "Epic")
    _add("F", "Feature", parent_id="E")
    _add("T", "Task", parent_id="F")

    with pytest.raises(BacklogOperationError, match="Violation"):
        update_item("F", parent_id="T")
    assert _parent("F") == "E"


def test_rejects_a_type_change_that_inverts_the_current_parent():
    _add("F", "Feature")
    _add("T", "Task", parent_id="F")

    with pytest.raises(BacklogOperationError, match="Violation"):
        update_item("T", item_type="Epic")
    assert load_backlog()["nodes"]["T"]["item_type"] == "Task"


def test_rejects_a_type_change_that_inverts_existing_children():
    _add("F", "Feature")
    _add("T", "Task", parent_id="F")

    with pytest.raises(BacklogOperationError, match="Violation"):
        update_item("F", item_type="Bug")
    assert load_backlog()["nodes"]["F"]["item_type"] == "Feature"


def test_rejects_an_unknown_type():
    _add("T", "Task")

    with pytest.raises(BacklogOperationError, match="Invalid item_type"):
        update_item("T", item_type="Saga")


def test_rejects_self_parenting():
    _add("F", "Feature")

    with pytest.raises(BacklogOperationError, match="own parent"):
        update_item("F", parent_id="F")


def test_allows_valid_changes_and_clearing_the_parent():
    _add("E", "Epic")
    _add("F", "Feature")
    _add("T", "Task", parent_id="F")

    update_item("F", parent_id="E")
    update_item("T", item_type="Bug")
    update_item("T", parent_id="")

    assert _parent("F") == "E"
    assert _parent("T") is None
    assert load_backlog()["nodes"]["T"]["item_type"] == "Bug"


def test_unrelated_updates_skip_hierarchy_checks():
    _add("T", "Task")
    update_item("T", impact=5)
    assert load_backlog()["nodes"]["T"]["impact"] == 5
