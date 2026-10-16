# Students Database CRUD API

Backend for managing student records with **FastAPI** and **SQLite**, plus an optional **Ollama** Q&A endpoint. Built for the EWB Edu Tech Python Backend internship assignment.

## Features
- Create, read (list / filter / single), update (PUT + PATCH) and delete students
- Input validation (email/phone format, DOB in the past, at least one contact method)
- Proper errors: `404` missing record, `409` duplicate email, `422` invalid input
- Data persists in a local SQLite file (`students.db`)
- Optional `/ask` endpoint: local LLM answers grounded in retrieved records (no model-written SQL)

## Prerequisites
- Python 3.10+
- (Optional) [Ollama](https://ollama.com) for the AI endpoint

## Installation
```bash
git clone <your-repo-url>
cd students-crud
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
python seed.py                   # optional: load 5 dummy students
uvicorn app.main:app --reload
```
Open interactive docs at http://127.0.0.1:8000/docs

## Project structure
```
app/
  main.py      routes and error handling
  schemas.py   Pydantic validation models
  crud.py      all SQL (parameterised queries)
  database.py  SQLite connection + table creation
  ai.py        optional Ollama extension
seed.py        dummy data loader
tests/         pytest suite
```

## API
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/students` | Create a student |
| GET | `/students` | List / filter (`name`, `course`, `dob_from`, `dob_to`, `skip`, `limit`) |
| GET | `/students/{student_id}` | View a student |
| PUT | `/students/{student_id}` | Replace all details |
| PATCH | `/students/{student_id}` | Update some details |
| DELETE | `/students/{student_id}` | Delete a student |
| POST | `/ask` | (Optional) Ask a question via Ollama |

Fields: `student_id` (auto), `name`, `date_of_birth`, `email` and/or `phone` (at least one), optional `course`, `address`, `enrollment_date`.

## Testing the API with curl
```bash
# Create
curl -X POST http://127.0.0.1:8000/students -H "Content-Type: application/json" \
  -d '{"name":"Asha Rao","date_of_birth":"2005-04-12","email":"asha@example.com","course":"B.Tech CSE"}'

# List and filter
curl http://127.0.0.1:8000/students
curl "http://127.0.0.1:8000/students?course=BBA&dob_from=2005-01-01"

# View one
curl http://127.0.0.1:8000/students/1

# Update (partial)
curl -X PATCH http://127.0.0.1:8000/students/1 -H "Content-Type: application/json" -d '{"course":"MBA"}'

# Delete
curl -X DELETE http://127.0.0.1:8000/students/1
```

## Automated tests
```bash
pytest -q
```

## Optional: Ollama AI extension
```bash
ollama pull llama3.2:1b
ollama serve                      # if not already running
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
  -d '{"question":"List students born after 2005"}'
```
Examples: "How many students are there?", "Who studies BBA?", "List students born after 2005".

**How it stays safe and grounded:** the backend parses the question with simple rules, runs fixed parameterised queries, and sends only the retrieved records (plus the total count) to the model, with instructions to answer only from that context. The model never writes or executes SQL. The response includes the `context` records used so answers can be verified. Configure with env vars `OLLAMA_URL` and `OLLAMA_MODEL`. If Ollama is not running, `/ask` returns `503`; the CRUD API is unaffected.

## Notes
- Only dummy data is included. Do not commit `students.db` or real student information (it is in `.gitignore`).
- Override the DB location with the `STUDENTS_DB` env var.
