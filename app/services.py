from datetime import date, datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import AttendanceRecord, Department, Employee, Role, User
from app.repositories import AttendanceRepository
from app.schemas import AttendanceOut, EmployeeIn, EmployeeOut


def commit_or_conflict(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, message) from None


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def employee_out(item: Employee) -> EmployeeOut:
    return EmployeeOut(id=item.id, employee_number=item.employee_number, user_id=item.user_id, name=item.user.name, email=item.user.email, role=item.user.role, department_id=item.department_id, job_title=item.job_title, hired_on=item.hired_on, created_at=item.created_at)


class EmployeeService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: EmployeeIn, actor: User) -> EmployeeOut:
        if data.role not in (Role.EMPLOYEE, Role.MANAGER):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Employee role must be EMPLOYEE or MANAGER")
        if self.db.get(Department, data.department_id) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Department does not exist")
        user = User(name=data.name.strip(), email=str(data.email).lower(), password_hash=hash_password(data.password), role=data.role)
        self.db.add(user)
        self.db.flush()
        item = Employee(employee_number=data.employee_number.strip().upper(), user_id=user.id, department_id=data.department_id, job_title=data.job_title.strip(), hired_on=data.hired_on, created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        commit_or_conflict(self.db, "Email or employee number already exists")
        self.db.refresh(item)
        return employee_out(item)

    def can_view(self, actor: User, employee: Employee) -> bool:
        if actor.role == Role.ADMIN or employee.user_id == actor.id:
            return True
        return actor.role == Role.MANAGER and employee.department.manager_id == actor.id


class AttendanceService:
    def __init__(self, db: Session):
        self.db = db

    def employee_for(self, actor: User) -> Employee:
        employee = self.db.scalar(select(Employee).where(Employee.user_id == actor.id))
        if employee is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No employee profile is assigned")
        return employee

    def clock_in(self, actor: User, note: str | None, now: datetime | None = None) -> AttendanceRecord:
        current = now or datetime.now(timezone.utc)
        employee = self.employee_for(actor)
        item = AttendanceRecord(employee_id=employee.id, work_date=current.date(), clock_in=current, clock_in_note=note.strip() if note else None)
        self.db.add(item)
        commit_or_conflict(self.db, "Employee has already clocked in for this date")
        self.db.refresh(item)
        return item

    def clock_out(self, record_id: int, actor: User, note: str | None, now: datetime | None = None) -> AttendanceRecord:
        item = self.db.scalar(select(AttendanceRecord).where(AttendanceRecord.id == record_id).with_for_update())
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Attendance record not found")
        employee = self.db.get_one(Employee, item.employee_id)
        if employee.user_id != actor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Employees may clock out only their own record")
        if item.clock_out is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Attendance record is already clocked out")
        current = now or datetime.now(timezone.utc)
        if current <= as_utc(item.clock_in):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Clock-out must be after clock-in")
        item.clock_out, item.clock_out_note = current, note.strip() if note else None
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(self, actor: User, start: date, end: date, employee_id: int | None, page: int, limit: int) -> dict:
        if start > end or (end - start).days > 366:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Date range must be valid and no longer than 366 days")
        items, total = AttendanceRepository(self.db).list_for_actor(actor, start, end, employee_id, page, limit)
        return {"data": [AttendanceOut.model_validate(item) for item in items], "meta": {"page": page, "limit": limit, "total": total, "total_pages": ceil(total / limit)}}

    def daily_report(self, actor: User, work_date: date) -> dict:
        query = select(AttendanceRecord).join(Employee).where(AttendanceRecord.work_date == work_date)
        if actor.role == Role.MANAGER:
            query = query.join(Department, Department.id == Employee.department_id).where(Department.manager_id == actor.id)
        elif actor.role != Role.ADMIN:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Manager or admin role required")
        items = list(self.db.scalars(query.order_by(Employee.employee_number)).all())
        completed = [item for item in items if item.clock_out]
        hours = sum((as_utc(item.clock_out) - as_utc(item.clock_in)).total_seconds() for item in completed) / 3600
        return {"date": work_date, "records": len(items), "open_records": len(items) - len(completed), "completed_records": len(completed), "total_hours": round(hours, 2)}
