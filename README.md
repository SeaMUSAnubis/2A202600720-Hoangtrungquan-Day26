# Day26 Lab: Database MCP Server with FastMCP and SQLite

This repository contains a complete lab implementation of a Model Context Protocol
(MCP) server. The server exposes a small SQLite database through three tools and
two schema resources.

## What is included

- FastMCP server: `implementation/mcp_server.py`
- SQLite schema and seed data: `implementation/init_db.py`
- Safe database adapter: `implementation/db.py`
- Repeatable verification script: `implementation/verify_server.py`
- Pytest coverage for successful and failing requests: `implementation/tests/test_server.py`
- MCP client examples: `client-configs/`
- MCP Inspector helper: `start_inspector.ps1`

## Data model

The demo database contains three relational tables:

- `students`: learner profile data with `name`, `cohort`, and `email`
- `courses`: course catalog data with `code`, `title`, and `credits`
- `enrollments`: student-course records with `score`, `status`, and `semester`

## Setup

Use Python 3.12 or newer.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python implementation/init_db.py
```

On macOS/Linux, replace `.venv/Scripts/python` with `.venv/bin/python`.

## Run the MCP server

The default transport is stdio, which is the easiest mode for local MCP clients.

```bash
.venv/Scripts/python implementation/mcp_server.py --reset-db
```

Optional HTTP transport for demos:

```bash
.venv/Scripts/python implementation/mcp_server.py --transport streamable-http --host 127.0.0.1 --port 8086
```

## MCP tools

### `search`

Search rows with optional filters, column selection, ordering, limit, and offset.

Example arguments:

```json
{
  "table": "students",
  "filters": [{"column": "cohort", "operator": "eq", "value": "A1"}],
  "columns": ["id", "name", "cohort"],
  "limit": 10,
  "order_by": "name"
}
```

Supported filter operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `like`, `in`.

### `insert`

Insert one row and return the inserted payload, including the generated ID.

Example arguments:

```json
{
  "table": "students",
  "values": {
    "name": "Minh Vo",
    "cohort": "C3",
    "email": "minh.vo@example.edu"
  }
}
```

### `aggregate`

Compute `count`, `avg`, `sum`, `min`, or `max`, optionally filtered or grouped.

Example arguments:

```json
{
  "table": "enrollments",
  "metric": "avg",
  "column": "score",
  "group_by": "semester"
}
```

## MCP resources

- `schema://database`: full database schema as JSON
- `schema://table/{table_name}`: dynamic resource template for one table schema

Useful examples:

- `schema://database`
- `schema://table/students`
- `schema://table/enrollments`

## Safety behavior

The adapter rejects unsafe or invalid requests before SQL execution:

- unknown table names
- unknown column names
- unsupported filter operators
- invalid aggregate metrics
- empty inserts
- explicit primary-key insert attempts
- invalid pagination

SQL values are passed as bound parameters. Table and column identifiers are
validated against the live SQLite schema before being quoted into SQL.

## Verification

Run automated tests:

```bash
.venv/Scripts/python -m pytest
```

Run the deliverable smoke check:

```bash
.venv/Scripts/python implementation/verify_server.py
```

Expected final line:

```text
All deliverable smoke checks passed.
```

The smoke check verifies seed tables, schema discovery, valid `search`,
valid `insert`, valid `aggregate`, and a failing invalid-table request.

## MCP Inspector

From the repository root:

```powershell
.\start_inspector.ps1
```

In Inspector, verify:

- tools `search`, `insert`, and `aggregate` are discoverable
- resource `schema://database` is readable
- resource template `schema://table/{table_name}` works for `students`
- a valid tool call succeeds
- an invalid tool call returns a clear error

## Client examples

Example configs are included in `client-configs/`:

- `client-configs/codex-config.toml`
- `client-configs/claude-mcp.json`
- `client-configs/gemini-cli.md`

For Codex, copy the `mcp_servers.sqlite_lab` block into `~/.codex/config.toml`
and update the Python/server paths if needed.

## Demo script

A short two-minute demo can show:

1. Start Inspector or an MCP client.
2. Confirm `search`, `insert`, and `aggregate` are visible.
3. Read `schema://database`.
4. Read `schema://table/students`.
5. Run `search` for cohort `A1`.
6. Insert a new student.
7. Run `aggregate` to compute average score.
8. Run an invalid request such as `table = "missing_table"` and show the clear error.

## Deliverable checklist

- Working FastMCP server
- SQLite database and reproducible seed data
- `search`, `insert`, and `aggregate` tools
- Full database schema resource
- Per-table schema resource template
- Safe validation and parameterized SQL values
- Automated tests and repeatable verification script
- Client configuration examples
- README setup, test, demo, and tool documentation
