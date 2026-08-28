import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)
    role: Literal["patient", "staff", "admin"] = "patient"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class UserResponse(BaseModel):
    name: str
    email: str
    role: str


class AppointmentCreate(BaseModel):
    doctor: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    date: dt.date

    @field_validator("date")
    @classmethod
    def reject_past_dates(cls, value: dt.date) -> dt.date:
        if value < dt.date.today():
            raise ValueError("Appointment date cannot be in the past")
        return value


class AppointmentUpdate(BaseModel):
    doctor: Optional[str] = Field(default=None, min_length=1)
    reason: Optional[str] = Field(default=None, min_length=1)
    date: Optional[dt.date] = None

    @field_validator("date")
    @classmethod
    def reject_past_dates(cls, value: Optional[dt.date]) -> Optional[dt.date]:
        if value is not None and value < dt.date.today():
            raise ValueError("Appointment date cannot be in the past")
        return value


class AppointmentResponse(BaseModel):
    id: int
    patient_email: str
    doctor: str
    reason: str
    date: dt.date
    status: str
    queue_number: int
