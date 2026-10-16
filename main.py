"""Students CRUD API (FastAPI + SQLite) with an optional Ollama Q&A endpoint."""
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from pydantic import ValidationError

from . import ai, crud
from .database import get_db, init_db
from .schemas import AskRequest, AskResponse, StudentCreate, StudentOut, StudentUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Students Database API", version="1.0.0", lifespan=lifespan)

NOT_FOUND = "Student not found"


def _save(fn, *args):
    """Run a write and translate DB constraint errors into HTTP 409."""
    try:
        return fn(*args)
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "A student with this email already exists")


@app.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(student: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    return _save(crud.create_student, db, student.model_dump())


@app.get("/students", response_model=list[StudentOut])
def list_students(
    name: Optional[str] = Query(None, description="Partial name match"),
    course: Optional[str] = Query(None, description="Partial course match"),
    dob_from: Optional[date] = Query(None, description="Born on/after this date"),
    dob_to: Optional[date] = Query(None, description="Born on/before this date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: sqlite3.Connection = Depends(get_db),
):
    return crud.list_students(db, name, course, dob_from, dob_to, skip, limit)


@app.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    student = crud.get_student(db, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return student


@app.put("/students/{student_id}", response_model=StudentOut)
def replace_student(student_id: int, student: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    updated = _save(crud.update_student, db, student_id, student.model_dump())
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return updated


@app.patch("/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, changes: StudentUpdate, db: sqlite3.Connection = Depends(get_db)):
    existing = crud.get_student(db, student_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    patch = changes.model_dump(exclude_unset=True)
    existing.pop("student_id")
    try:  # re-validate the merged record (e.g. contact info must remain)
        merged = StudentCreate.model_validate({**existing, **patch})
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            exc.errors(include_url=False, include_context=False, include_input=False))
    return _save(crud.update_student, db, student_id, merged.model_dump())


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    if not crud.delete_student(db, student_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/ask", response_model=AskResponse, tags=["AI (optional)"])
def ask(body: AskRequest, db: sqlite3.Connection = Depends(get_db)):
    """Natural-language questions answered by a local Ollama model, grounded in retrieved records."""
    facts, records = ai.retrieve_context(db, body.question)
    try:
        answer = ai.ask_ollama(body.question, facts, records)
    except ai.OllamaUnavailable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Ollama is not reachable. Start it with `ollama serve` and pull the model.")
    return AskResponse(answer=answer, records_used=len(records), context=records)
