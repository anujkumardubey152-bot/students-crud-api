"""All SQL lives here. Every query is parameterised."""
import sqlite3
from datetime import date
from typing import Optional

FIELDS = ["name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date"]


def _row(row: sqlite3.Row) -> dict:
    return dict(row)


def create_student(conn: sqlite3.Connection, data: dict) -> dict:
    values = [data.get(f) for f in FIELDS]
    values = [v.isoformat() if isinstance(v, date) else v for v in values]
    cur = conn.execute(
        f"INSERT INTO students ({', '.join(FIELDS)}) VALUES ({', '.join('?' * len(FIELDS))})",
        values,
    )
    conn.commit()
    return get_student(conn, cur.lastrowid)


def get_student(conn: sqlite3.Connection, student_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    return _row(row) if row else None


def list_students(
    conn: sqlite3.Connection,
    name: Optional[str] = None,
    course: Optional[str] = None,
    dob_from: Optional[date] = None,
    dob_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    clauses, params = [], []
    if name:
        clauses.append("name LIKE ?")
        params.append(f"%{name}%")
    if course:
        clauses.append("course LIKE ?")
        params.append(f"%{course}%")
    if dob_from:
        clauses.append("date_of_birth >= ?")
        params.append(dob_from.isoformat())
    if dob_to:
        clauses.append("date_of_birth <= ?")
        params.append(dob_to.isoformat())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM students {where} ORDER BY student_id LIMIT ? OFFSET ?",
        (*params, limit, skip),
    ).fetchall()
    return [_row(r) for r in rows]


def count_students(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]


def distinct_courses(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL").fetchall()
    return [r[0] for r in rows]


def update_student(conn: sqlite3.Connection, student_id: int, data: dict) -> Optional[dict]:
    if get_student(conn, student_id) is None:
        return None
    data = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in data.items() if k in FIELDS}
    if data:
        sets = ", ".join(f"{k} = ?" for k in data)
        conn.execute(f"UPDATE students SET {sets} WHERE student_id = ?", (*data.values(), student_id))
        conn.commit()
    return get_student(conn, student_id)


def delete_student(conn: sqlite3.Connection, student_id: int) -> bool:
    cur = conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.commit()
    return cur.rowcount > 0
