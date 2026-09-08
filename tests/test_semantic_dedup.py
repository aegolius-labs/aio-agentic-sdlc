import sqlite3

import pytest
from mcp.client import Client

from aio_agentic_sdlc import semantic_dedup
from aio_agentic_sdlc.mcp_server import mcp


def test_missing_extension_support_closes_connection(tmp_path, monkeypatch):
    class WithoutExtensionLoading(sqlite3.Connection):
        def __getattribute__(self, name):
            if name == "enable_load_extension":
                raise AttributeError(name)
            return super().__getattribute__(name)

    connection = sqlite3.connect(":memory:", factory=WithoutExtensionLoading)
    monkeypatch.setattr(semantic_dedup.sqlite3, "connect", lambda _: connection)

    with pytest.raises(
        semantic_dedup.SemanticCacheError, match="Python with SQLite extension loading"
    ):
        semantic_dedup.get_db(str(tmp_path))
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")


@pytest.mark.parametrize("failure_stage", ["load", "schema"])
def test_failed_initialization_closes_connection(tmp_path, monkeypatch, failure_stage):
    toggles = []

    class ObservedConnection(sqlite3.Connection):
        def enable_load_extension(self, enabled):
            toggles.append(enabled)
            return super().enable_load_extension(enabled)

        def execute(self, sql, *args):
            if failure_stage == "schema" and "CREATE" in sql:
                raise sqlite3.OperationalError("schema-initialization-failed")
            return super().execute(sql, *args)

    connection = sqlite3.connect(":memory:", factory=ObservedConnection)
    monkeypatch.setattr(semantic_dedup.sqlite3, "connect", lambda _: connection)
    if failure_stage == "load":

        def fail_loading(_connection):
            raise sqlite3.OperationalError("private-loader-detail")

        monkeypatch.setattr(semantic_dedup.sqlite_vec, "load", fail_loading)

    expected = (
        semantic_dedup.SemanticCacheError
        if failure_stage == "load"
        else sqlite3.OperationalError
    )
    with pytest.raises(expected):
        semantic_dedup.get_db(str(tmp_path))
    assert toggles == [True, False]
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        connection.execute("SELECT 1")


@pytest.mark.asyncio
async def test_mcp_reports_sqlite_prerequisite_without_internal_details(
    tmp_path, monkeypatch
):
    def fail_loading(_connection):
        raise sqlite3.OperationalError("private-loader-detail")

    monkeypatch.setattr(semantic_dedup.sqlite_vec, "load", fail_loading)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "check_duplicate_prd",
            {"proposed_content": "A requirement", "project_path": str(tmp_path)},
        )
    assert result.is_error is True
    message = "".join(block.text for block in result.content if hasattr(block, "text"))
    assert "could not load sqlite-vec" in message
    assert "private-loader-detail" not in message
    assert str(tmp_path) not in message
