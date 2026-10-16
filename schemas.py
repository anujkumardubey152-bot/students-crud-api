"""Pydantic models: request validation and response shapes."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
PHONE_PATTERN = r"^\+?[0-9][0-9\- ]{6,14}$"


class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    date_of_birth: date
    email: Optional[str] = Field(default=None, pattern=EMAIL_PATTERN)
    phone: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    enrollment_date: Optional[date] = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("name must have at least 2 characters")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: Optional[str]) -> Optional[str]:
        return v.lower() if v else v

    @field_validator("date_of_birth")
    @classmethod
    def dob_in_past(cls, v: date) -> date:
        if v >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return v

    @model_validator(mode="after")
    def need_contact(self):
        if not self.email and not self.phone:
            raise ValueError("provide at least one of email or phone")
        return self


class StudentUpdate(BaseModel):
    """PATCH body: every field optional."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    date_of_birth: Optional[date] = None
    email: Optional[str] = Field(default=None, pattern=EMAIL_PATTERN)
    phone: Optional[str] = Field(default=None, pattern=PHONE_PATTERN)
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    enrollment_date: Optional[date] = None


class StudentOut(StudentCreate):
    student_id: int


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskResponse(BaseModel):
    answer: str
    records_used: int
    context: list[dict]
