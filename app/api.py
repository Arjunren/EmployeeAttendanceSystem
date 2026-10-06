from datetime import date, timedelta
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import bearer, check_login_rate, dummy_hash, get_current_user, issue_token, require_roles, revoke_token, verify_password
from app.database import get_db
from app.models import Department, Employee, Role, User
from app.schemas import AttendanceOut, ClockIn, ClockOut, DepartmentIn, DepartmentOut, EmployeeIn, LoginIn, UserOut
from app.services import AttendanceService, EmployeeService, commit_or_conflict, employee_out

router = APIRouter(prefix="/api")


@router.post("/auth/login")
def login(data: LoginIn, request: Request, db: Annotated[Session, Depends(get_db)]) -> dict:
    check_login_rate(request)
    user = db.scalar(select(User).where(func.lower(User.email) == str(data.email).lower()))
    if user is None:
        verify_password(data.password, dummy_hash)
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")
    return {"data": {"access_token": issue_token(db, user), "token_type": "Bearer", "user": UserOut.model_validate(user)}}


@router.post("/auth/logout", status_code=204)
def logout(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)], _user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> None:
    revoke_token(db, credentials.credentials)


@router.get("/departments")
def departments(_actor: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"data": [DepartmentOut.model_validate(item) for item in db.scalars(select(Department).order_by(Department.name)).all()]}


@router.post("/departments", status_code=201)
def create_department(data: DepartmentIn, admin: Annotated[User, Depends(require_roles(Role.ADMIN))], db: Annotated[Session, Depends(get_db)]) -> dict:
    if data.manager_id is not None:
        manager = db.get(User, data.manager_id)
        if manager is None or manager.role != Role.MANAGER:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "manager_id must reference a manager")
    item = Department(name=data.name.strip(), manager_id=data.manager_id, created_by=admin.id)
    db.add(item)
    commit_or_conflict(db, "Department already exists")
    db.refresh(item)
    return {"data": DepartmentOut.model_validate(item)}


@router.get("/employees")
def employees(actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.MANAGER))], db: Annotated[Session, Depends(get_db)], search: str = Query("", max_length=120), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)) -> dict:
    query = select(Employee).join(User, User.id == Employee.user_id)
    count = select(func.count()).select_from(Employee).join(User, User.id == Employee.user_id)
    conditions = [(Employee.employee_number.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))]
    if actor.role == Role.MANAGER:
        conditions.append(Employee.department_id.in_(select(Department.id).where(Department.manager_id == actor.id)))
    items = db.scalars(query.where(*conditions).order_by(Employee.employee_number).offset((page - 1) * limit).limit(limit)).all()
    total = db.scalar(count.where(*conditions)) or 0
    return {"data": [employee_out(item) for item in items], "meta": {"page": page, "limit": limit, "total": total, "total_pages": ceil(total / limit)}}


@router.post("/employees", status_code=201)
def create_employee(data: EmployeeIn, admin: Annotated[User, Depends(require_roles(Role.ADMIN))], db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"data": EmployeeService(db).create(data, admin)}


@router.get("/attendance")
def attendance(actor: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], start: date = Query(default_factory=lambda: date.today() - timedelta(days=30)), end: date = Query(default_factory=date.today), employee_id: int | None = Query(None, ge=1), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)) -> dict:
    return AttendanceService(db).list(actor, start, end, employee_id, page, limit)


@router.post("/attendance/clock-in", status_code=201)
def clock_in(data: ClockIn, actor: Annotated[User, Depends(require_roles(Role.EMPLOYEE, Role.MANAGER))], db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"data": AttendanceOut.model_validate(AttendanceService(db).clock_in(actor, data.note))}


@router.patch("/attendance/{record_id}/clock-out")
def clock_out(record_id: int, data: ClockOut, actor: Annotated[User, Depends(require_roles(Role.EMPLOYEE, Role.MANAGER))], db: Annotated[Session, Depends(get_db)]) -> dict:
    return {"data": AttendanceOut.model_validate(AttendanceService(db).clock_out(record_id, actor, data.note))}


@router.get("/reports/daily")
def daily_report(actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.MANAGER))], db: Annotated[Session, Depends(get_db)], work_date: date = Query(default_factory=date.today)) -> dict:
    return {"data": AttendanceService(db).daily_report(actor, work_date)}


@router.get("/dashboard")
def dashboard(actor: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]) -> dict:
    if actor.role == Role.EMPLOYEE:
        records = AttendanceService(db).list(actor, date.today() - timedelta(days=30), date.today(), None, 1, 100)
        return {"data": {"last_30_days": records["meta"]["total"]}}
    return {"data": AttendanceService(db).daily_report(actor, date.today())}
