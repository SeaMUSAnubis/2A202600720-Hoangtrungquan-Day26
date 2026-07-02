"""Create and seed the SQLite database used by the MCP lab server."""

from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "lab.sqlite3"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    status TEXT NOT NULL DEFAULT 'active',
    semester TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE (student_id, course_id, semester)
);
"""


SEED_SQL = """
INSERT OR IGNORE INTO students (id, name, cohort, email) VALUES
    (1, 'An Nguyen', 'A1', 'an.nguyen@example.edu'),
    (2, 'Binh Tran', 'A1', 'binh.tran@example.edu'),
    (3, 'Chi Le', 'B2', 'chi.le@example.edu'),
    (4, 'Dung Pham', 'B2', 'dung.pham@example.edu'),
    (5, 'Linh Hoang', 'A1', 'linh.hoang@example.edu');

INSERT OR IGNORE INTO courses (id, code, title, credits) VALUES
    (1, 'AI101', 'Introduction to AI', 3),
    (2, 'DB201', 'Databases for AI Systems', 4),
    (3, 'MCP301', 'Tool Integration with MCP', 2);

INSERT OR IGNORE INTO enrollments (id, student_id, course_id, score, status, semester) VALUES
    (1, 1, 1, 86.5, 'active', '2026-Summer'),
    (2, 1, 3, 91.0, 'active', '2026-Summer'),
    (3, 2, 1, 78.0, 'active', '2026-Summer'),
    (4, 2, 2, 82.5, 'active', '2026-Summer'),
    (5, 3, 2, 88.0, 'active', '2026-Summer'),
    (6, 4, 3, 73.5, 'inactive', '2026-Summer'),
    (7, 5, 1, 94.0, 'active', '2026-Summer'),
    (8, 5, 3, 96.0, 'active', '2026-Summer');
"""


def create_database(db_path: str | Path = DEFAULT_DB_PATH, reset: bool = False) -> Path:
    """Create a reproducible SQLite database and seed demo data."""

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if reset and path.exists():
        path.unlink()

    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.executescript(SEED_SQL)
        connection.commit()

    return path


if __name__ == "__main__":
    created_path = create_database(reset=True)
    print(f"Database ready: {created_path}")

