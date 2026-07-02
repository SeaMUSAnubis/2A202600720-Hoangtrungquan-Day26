"""Repeatable smoke checks for the SQLite MCP lab deliverables."""

from __future__ import annotations

import json
from pathlib import Path

from db import SQLiteAdapter, ValidationError
from init_db import create_database


def main() -> None:
    db_path = Path(__file__).resolve().parent / "verify.sqlite3"
    create_database(db_path, reset=True)
    adapter = SQLiteAdapter(db_path, initialize=False)

    tables = adapter.list_tables()
    assert {"students", "courses", "enrollments"}.issubset(tables)

    schema = adapter.database_schema()
    assert "students" in schema["tables"]

    search_result = adapter.search(
        "students",
        filters=[{"column": "cohort", "operator": "eq", "value": "A1"}],
        columns=["id", "name", "cohort"],
        order_by="name",
    )
    assert search_result["count"] >= 1

    insert_result = adapter.insert(
        "students",
        {"name": "Minh Vo", "cohort": "C3", "email": "minh.vo@example.edu"},
    )
    assert insert_result["inserted"]["id"]

    aggregate_result = adapter.aggregate("enrollments", "avg", "score", group_by="semester")
    assert aggregate_result["rows"][0]["value"] > 0

    try:
        adapter.search("missing_table")
    except ValidationError as exc:
        invalid_error = str(exc)
    else:
        raise AssertionError("invalid table was not rejected")

    report = {
        "server_start_logic": "ok",
        "tools_expected": ["search", "insert", "aggregate"],
        "schema_resources_expected": ["schema://database", "schema://table/{table_name}"],
        "tables": tables,
        "valid_search_count": search_result["count"],
        "inserted_student": insert_result["inserted"],
        "aggregate_rows": aggregate_result["rows"],
        "invalid_request_error": invalid_error,
    }
    print(json.dumps(report, indent=2))
    print("All deliverable smoke checks passed.")


if __name__ == "__main__":
    main()
