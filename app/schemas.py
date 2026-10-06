from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    role: Role
    is_active: bool


class DepartmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    manager_id: int | None = Field(default=None, ge=1)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    manager_id: int | None


class EmployeeIn(BaseModel):
    employee_number: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)
    role: Role = Role.EMPLOYEE
    department_id: int = Field(ge=1)
    job_title: str = Field(min_length=2, max_length=120)
    hired_on: date


class EmployeeOut(BaseModel):
    id: int
    employee_number: str
    user_id: int
    name: str
    email: str
    role: Role
    department_id: int
    job_title: str
    hired_on: date
    created_at: datetime


class ClockIn(BaseModel):
    note: str | None = Field(default=None, max_length=250)


class ClockOut(BaseModel):
    note: str | None = Field(default=None, max_length=250)


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    work_date: date
    clock_in: datetime
    clock_out: datetime | None
    clock_in_note: str | None
    clock_out_note: str | None

