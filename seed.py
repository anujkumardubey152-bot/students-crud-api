"""Load dummy students (fake data only)."""
from app.database import get_connection, init_db
from app import crud

DUMMY = [
    ("Aarav Sharma", "2004-03-14", "aarav@example.com", "9876500001", "B.Tech CSE", "2022-08-01"),
    ("Diya Verma", "2005-07-22", "diya@example.com", "9876500002", "B.Tech CSE", "2023-08-01"),
    ("Kabir Singh", "2006-01-09", "kabir@example.com", None, "BBA", "2024-08-01"),
    ("Meera Iyer", "2003-11-30", None, "9876500004", "B.Sc Physics", "2021-08-01"),
    ("Rohan Gupta", "2005-12-05", "rohan@example.com", "9876500005", "BBA", "2023-08-01"),
]

if __name__ == "__main__":
    init_db()
    conn = get_connection()
    if crud.count_students(conn) == 0:
        for name, dob, email, phone, course, enrolled in DUMMY:
            crud.create_student(conn, dict(name=name, date_of_birth=dob, email=email,
                                           phone=phone, course=course, enrollment_date=enrolled))
        print(f"Seeded {len(DUMMY)} dummy students.")
    else:
        print("Database already has data; skipping.")
