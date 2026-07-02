"""FastMCP server exposing safe SQLite search, insert, aggregate, and schema resources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover - compatibility with mcp[cli]
    from mcp.server.fastmcp import FastMCP

from db import SQLiteAdapter, ValidationError
from init_db import DEFAULT_DB_PATH, create_database


mcp = FastMCP("SQLite Lab MCP Server")
adapter = SQLiteAdapter(DEFAULT_DB_PATH)


def _safe_call(callback):
    try:
        return callback()
    except ValidationError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows in a validated table using safe filters, ordering, and pagination."""

    return _safe_call(
        lambda: {
            "ok": True,
            "result": adapter.search(table, filters, columns, limit, offset, order_by, descending),
        }
    )


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one row into a validated table and return the inserted payload."""

    return _safe_call(lambda: {"ok": True, "result": adapter.insert(table, values)})


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    """Compute count, avg, sum, min, or max over a validated table."""

    return _safe_call(
        lambda: {
            "ok": True,
            "result": adapter.aggregate(table, metric, column, filters, group_by),
        }
    )


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return the full SQLite database schema as JSON text."""

    return json.dumps(adapter.database_schema(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return one table schema as JSON text."""

    return json.dumps(adapter.get_table_schema(table_name), indent=2)


def configure_database(db_path: str | Path = DEFAULT_DB_PATH, reset: bool = False) -> None:
    """Point the server at a database path; useful for tests and demos."""

    global adapter
    path = create_database(db_path, reset=reset)
    adapter = SQLiteAdapter(path, initialize=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite FastMCP lab server")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    parser.add_argument("--reset-db", action="store_true", help="recreate and seed the database before serving")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http", "sse"],
        help="FastMCP transport",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP/SSE host")
    parser.add_argument("--port", type=int, default=8086, help="HTTP/SSE port")
    args = parser.parse_args()

    configure_database(args.db, reset=args.reset_db)
    if args.transport == "stdio":
        mcp.run()
    else:
        try:
            mcp.settings.host = args.host
            mcp.settings.port = args.port
        except AttributeError:
            pass
        mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()

