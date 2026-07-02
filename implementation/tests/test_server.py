from __future__ import annotations

import sys
from hashlib import sha1
from pathlib import Path

import pytest


IMPLEMENTATION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(IMPLEMENTATION_DIR))

from db import SQLiteAdapter, ValidationError
from init_db import create_database


@pytest.fixture()
def adapter(request):
    db_dir = IMPLEMENTATION_DIR / ".test-data"
    db_dir.mkdir(exist_ok=True)
    db_name = sha1(request.node.nodeid.encode("utf-8")).hexdigest()[:12]
    db_path = db_dir / f"{db_name}.sqlite3"
    create_database(db_path, reset=True)
    return SQLiteAdapter(db_path, initialize=False)


def test_search_filters_ordering_and_pagination(adapter):
    result = adapter.search(
        "students",
        filters=[{"column": "cohort", "operator": "eq", "value": "A1"}],
        columns=["id", "name", "cohort"],
        limit=2,
        offset=0,
        order_by="name",
    )

    assert result["count"] == 2
    assert result["columns"] == ["id", "name", "cohort"]
    assert all(row["cohort"] == "A1" for row in result["rows"])


def test_insert_returns_inserted_payload(adapter):
    result = adapter.insert(
        "students",
        {"name": "Minh Vo", "cohort": "C3", "email": "minh.vo@example.edu"},
    )

    assert result["inserted"]["id"] > 0
    assert result["inserted"]["name"] == "Minh Vo"


def test_aggregate_supports_avg_grouped(adapter):
    result = adapter.aggregate("students", "count", group_by="cohort")

    assert {row["cohort"] for row in result["rows"]} >= {"A1", "B2"}
    assert all(row["value"] > 0 for row in result["rows"])


def test_schema_resources_have_columns(adapter):
    schema = adapter.database_schema()
    student_columns = {column["name"] for column in schema["tables"]["students"]["columns"]}

    assert {"id", "name", "cohort", "email"}.issubset(student_columns)
    assert adapter.get_table_schema("courses")["table"] == "courses"


@pytest.mark.parametrize(
    ("callback", "message"),
    [
        (lambda adapter: adapter.search("missing"), "unknown table"),
        (
            lambda adapter: adapter.search(
                "students",
                filters=[{"column": "name", "operator": "regex", "value": "A"}],
            ),
            "unsupported filter operator",
        ),
        (lambda adapter: adapter.search("students", columns=["password"]), "unknown column"),
        (lambda adapter: adapter.insert("students", {}), "non-empty object"),
        (lambda adapter: adapter.aggregate("students", "median", "id"), "unsupported aggregate"),
    ],
)
def test_invalid_requests_are_rejected(adapter, callback, message):
    with pytest.raises(ValidationError, match=message):
        callback(adapter)
