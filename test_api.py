import pytest
from fastapi.testclient import TestClient

from app.main import app

VALID = {"name": "Test User", "date_of_birth": "2004-05-01",
         "email": "test@example.com", "course": "B.Tech CSE"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDENTS_DB", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


def test_full_crud_cycle(client):
    r = client.post("/students", json=VALID)
    assert r.status_code == 201
    sid = r.json()["student_id"]

    assert client.get(f"/students/{sid}").json()["name"] == "Test User"
    assert len(client.get("/students").json()) == 1

    r = client.patch(f"/students/{sid}", json={"course": "MBA"})
    assert r.status_code == 200 and r.json()["course"] == "MBA"

    r = client.put(f"/students/{sid}", json={**VALID, "name": "New Name"})
    assert r.json()["name"] == "New Name"

    assert client.delete(f"/students/{sid}").status_code == 204
    assert client.get(f"/students/{sid}").status_code == 404


def test_filters(client):
    client.post("/students", json=VALID)
    client.post("/students", json={**VALID, "name": "Old One", "email": "o@example.com",
                                   "date_of_birth": "2001-01-01", "course": "BBA"})
    assert len(client.get("/students", params={"course": "BBA"}).json()) == 1
    assert len(client.get("/students", params={"dob_from": "2003-01-01"}).json()) == 1
    assert len(client.get("/students", params={"name": "user"}).json()) == 1


def test_validation_errors(client):
    assert client.post("/students", json={**VALID, "email": "bad"}).status_code == 422
    assert client.post("/students", json={"name": "No Contact", "date_of_birth": "2004-01-01"}).status_code == 422
    assert client.post("/students", json={**VALID, "date_of_birth": "2999-01-01"}).status_code == 422


def test_duplicate_email_and_missing_records(client):
    client.post("/students", json=VALID)
    assert client.post("/students", json=VALID).status_code == 409
    assert client.get("/students/999").status_code == 404
    assert client.patch("/students/999", json={"course": "X"}).status_code == 404
    assert client.put("/students/999", json=VALID).status_code == 404
    assert client.delete("/students/999").status_code == 404


def test_patch_cannot_remove_all_contact(client):
    sid = client.post("/students", json=VALID).json()["student_id"]
    assert client.patch(f"/students/{sid}", json={"email": None}).status_code == 422


def test_data_persists_between_app_restarts(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDENTS_DB", str(tmp_path / "p.db"))
    with TestClient(app) as c:
        c.post("/students", json=VALID)
    with TestClient(app) as c:
        assert len(c.get("/students").json()) == 1


def test_ai_retrieval_is_grounded(client, monkeypatch):
    from app import ai
    client.post("/students", json={**VALID, "date_of_birth": "2006-02-02"})
    client.post("/students", json={**VALID, "name": "Older Person", "email": "x@example.com",
                                   "date_of_birth": "2000-02-02"})
    captured = {}
    monkeypatch.setattr(ai, "ask_ollama", lambda q, f, r: captured.update(f=f, r=r) or "ok")
    body = client.post("/ask", json={"question": "List students born after 2005"}).json()
    assert body["records_used"] == 1 and captured["f"]["total_students"] == 2


def test_ask_returns_503_when_ollama_down(client, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:1")
    from app import ai
    monkeypatch.setattr(ai, "OLLAMA_URL", "http://127.0.0.1:1")
    assert client.post("/ask", json={"question": "How many students are there?"}).status_code == 503
