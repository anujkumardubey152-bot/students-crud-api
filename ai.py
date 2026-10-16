"""Optional Ollama extension.

Safety design: the model NEVER writes or runs SQL. The backend interprets the
question with simple rules, runs fixed parameterised queries from crud.py, and
hands only the retrieved records to the model as context.
"""
import os
import re
import sqlite3
from datetime import date

import httpx

from . import crud

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
MAX_CONTEXT_RECORDS = 50

SYSTEM_PROMPT = (
    "You answer questions about a student database. Use ONLY the facts provided "
    "in the context. If the context does not contain the answer, say you don't "
    "have that information. Be concise and do not invent students or numbers."
)


class OllamaUnavailable(Exception):
    pass


def retrieve_context(conn: sqlite3.Connection, question: str) -> tuple[dict, list[dict]]:
    """Return (facts, records) relevant to the question using fixed queries."""
    q = question.lower()
    facts = {"total_students": crud.count_students(conn)}
    filters: dict = {}

    m = re.search(r"born\s+(after|before|in)\s+(\d{4})", q)
    if m:
        kind, year = m.group(1), int(m.group(2))
        if kind == "after":
            filters["dob_from"] = date(year + 1, 1, 1)
        elif kind == "before":
            filters["dob_to"] = date(year - 1, 12, 31)
        else:
            filters["dob_from"], filters["dob_to"] = date(year, 1, 1), date(year, 12, 31)

    for course in crud.distinct_courses(conn):
        if course.lower() in q:
            filters["course"] = course
            break

    records = crud.list_students(conn, limit=MAX_CONTEXT_RECORDS, **filters)
    if not filters:
        # Name lookup: match any stored full name mentioned in the question.
        named = [r for r in records if r["name"].lower() in q]
        if named:
            records = named
    else:
        facts["matching_students"] = len(crud.list_students(conn, limit=100000, **filters))
    return facts, records


def ask_ollama(question: str, facts: dict, records: list[dict]) -> str:
    context = "Facts: " + str(facts) + "\nRecords:\n" + "\n".join(
        f"- id={r['student_id']}, name={r['name']}, dob={r['date_of_birth']}, "
        f"course={r['course']}, email={r['email']}, phone={r['phone']}"
        for r in records
    )
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context}\n\nQuestion: {question}"},
        ],
    }
    try:
        resp = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
    except (httpx.HTTPError, OSError) as exc:
        raise OllamaUnavailable(str(exc)) from exc
    return resp.json()["message"]["content"].strip()
