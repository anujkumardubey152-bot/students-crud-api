"""SQLite connection handling and schema creation."""
import os
import sqlite3
from typing import Iterator


def db_path() -> str:
    # Read at call time so tests can point to a temporary database.
    return os.getenv("STUDENTS_DB", "students.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                date_of_birth   TEXT NOT NULL,          -- ISO date YYYY-MM-DD
                email           TEXT UNIQUE,
                phone           TEXT,
                course          TEXT,
                address         TEXT,
                enrollment_date TEXT,
                CHECK (email IS NOT NULL OR phone IS NOT NULL)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
