"""SQLite adapter with validation for the FastMCP lab tools."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from init_db import DEFAULT_DB_PATH, create_database


class ValidationError(ValueError):
    """Raised when a database request cannot be safely executed."""


SUPPORTED_OPERATORS = {
    "eq": "=",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "like": "LIKE",
    "in": "IN",
}
SUPPORTED_METRICS = {"count", "avg", "sum", "min", "max"}
MAX_LIMIT = 100


class SQLiteAdapter:
    """Small validated SQLite data access layer for the lab MCP tools."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, initialize: bool = True):
        self.db_path = Path(db_path)
        if initialize and not self.db_path.exists():
            create_database(self.db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def list_tables(self) -> list[str]:
        sql = """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """
        with self.connect() as connection:
            rows = connection.execute(sql).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> dict[str, Any]:
        self._validate_table(table)
        with self.connect() as connection:
            columns = connection.execute(f"PRAGMA table_info({self._quote_identifier(table)})").fetchall()
            foreign_keys = connection.execute(f"PRAGMA foreign_key_list({self._quote_identifier(table)})").fetchall()
        return {
            "table": table,
            "columns": [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "primary_key": bool(row["pk"]),
                }
                for row in columns
            ],
            "foreign_keys": [
                {
                    "column": row["from"],
                    "references_table": row["table"],
                    "references_column": row["to"],
                }
                for row in foreign_keys
            ],
        }

    def database_schema(self) -> dict[str, Any]:
        return {
            "database": str(self.db_path),
            "tables": {table: self.get_table_schema(table) for table in self.list_tables()},
        }

    def search(
        self,
        table: str,
        filters: list[dict[str, Any]] | None = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        self._validate_table(table)
        selected_columns = self._validate_selected_columns(table, columns)
        limit, offset = self._validate_pagination(limit, offset)

        where_clause, params = self._build_where_clause(table, filters)
        order_clause = ""
        if order_by:
            self._validate_column(table, order_by)
            direction = "DESC" if descending else "ASC"
            order_clause = f" ORDER BY {self._quote_identifier(order_by)} {direction}"

        select_sql = ", ".join(self._quote_identifier(column) for column in selected_columns)
        sql = (
            f"SELECT {select_sql} FROM {self._quote_identifier(table)}"
            f"{where_clause}{order_clause} LIMIT ? OFFSET ?"
        )
        query_params = [*params, limit, offset]
        with self.connect() as connection:
            rows = connection.execute(sql, query_params).fetchall()

        return {
            "table": table,
            "columns": selected_columns,
            "limit": limit,
            "offset": offset,
            "count": len(rows),
            "rows": [dict(row) for row in rows],
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        self._validate_table(table)
        if not isinstance(values, dict) or not values:
            raise ValidationError("insert values must be a non-empty object")

        for column in values:
            self._validate_column(table, column, allow_primary_key=False)

        columns = list(values)
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(self._quote_identifier(column) for column in columns)
        sql = f"INSERT INTO {self._quote_identifier(table)} ({column_sql}) VALUES ({placeholders})"

        try:
            with self.connect() as connection:
                cursor = connection.execute(sql, [values[column] for column in columns])
                row_id = cursor.lastrowid
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValidationError(f"insert failed: {exc}") from exc

        inserted = dict(values)
        if "id" not in inserted:
            inserted["id"] = row_id
        return {"table": table, "inserted": inserted}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        self._validate_table(table)
        metric = metric.lower()
        if metric not in SUPPORTED_METRICS:
            raise ValidationError(f"unsupported aggregate metric: {metric}")

        if metric == "count" and column is None:
            target_sql = "*"
        else:
            if not column:
                raise ValidationError(f"{metric} requires a column")
            self._validate_column(table, column)
            target_sql = self._quote_identifier(column)

        select_parts = []
        group_clause = ""
        if group_by:
            self._validate_column(table, group_by)
            select_parts.append(self._quote_identifier(group_by))
            group_clause = f" GROUP BY {self._quote_identifier(group_by)}"

        select_parts.append(f"{metric.upper()}({target_sql}) AS value")
        where_clause, params = self._build_where_clause(table, filters)
        sql = f"SELECT {', '.join(select_parts)} FROM {self._quote_identifier(table)}{where_clause}{group_clause}"

        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        return {
            "table": table,
            "metric": metric,
            "column": column,
            "group_by": group_by,
            "rows": [dict(row) for row in rows],
        }

    def _build_where_clause(self, table: str, filters: list[dict[str, Any]] | None) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        if not isinstance(filters, list):
            raise ValidationError("filters must be a list of filter objects")

        clauses: list[str] = []
        params: list[Any] = []
        for item in filters:
            if not isinstance(item, dict):
                raise ValidationError("each filter must be an object")
            column = item.get("column")
            operator = item.get("operator", "eq")
            value = item.get("value")
            self._validate_column(table, column)
            if operator not in SUPPORTED_OPERATORS:
                raise ValidationError(f"unsupported filter operator: {operator}")

            quoted_column = self._quote_identifier(column)
            if operator == "in":
                if not isinstance(value, list) or not value:
                    raise ValidationError("in filter value must be a non-empty list")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f"{quoted_column} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{quoted_column} {SUPPORTED_OPERATORS[operator]} ?")
                params.append(value)

        return " WHERE " + " AND ".join(clauses), params

    def _validate_table(self, table: str) -> None:
        if not isinstance(table, str) or table not in self.list_tables():
            raise ValidationError(f"unknown table: {table}")

    def _validate_column(self, table: str, column: str | None, allow_primary_key: bool = True) -> None:
        if not isinstance(column, str):
            raise ValidationError("column name must be a string")
        schema = self.get_table_schema(table)
        valid_columns = {item["name"]: item for item in schema["columns"]}
        if column not in valid_columns:
            raise ValidationError(f"unknown column for {table}: {column}")
        if not allow_primary_key and valid_columns[column]["primary_key"]:
            raise ValidationError(f"cannot insert explicit primary key column: {column}")

    def _validate_selected_columns(self, table: str, columns: list[str] | None) -> list[str]:
        schema_columns = [item["name"] for item in self.get_table_schema(table)["columns"]]
        if columns is None:
            return schema_columns
        if not isinstance(columns, list) or not columns:
            raise ValidationError("columns must be a non-empty list when provided")
        for column in columns:
            self._validate_column(table, column)
        return columns

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> tuple[int, int]:
        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("limit must be a positive integer")
        if limit > MAX_LIMIT:
            raise ValidationError(f"limit cannot exceed {MAX_LIMIT}")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset must be a non-negative integer")
        return limit, offset

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        if not identifier.replace("_", "").isalnum():
            raise ValidationError(f"unsafe identifier: {identifier}")
        return f'"{identifier}"'

