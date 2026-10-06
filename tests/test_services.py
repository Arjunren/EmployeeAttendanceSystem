from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models import Department, Employee, Role, User
from app.services import AttendanceService


def setup_people(db):
    admin = User(name="Admin", email="admin@example.com", password_hash="x", role=Role.ADMIN)
    manager = User(name="Manager", email="manager@example.com", password_hash="x", role=Role.MANAGER)
    worker = User(name="Worker", email="worker@example.com", password_hash="x", role=Role.EMPLOYEE)
    outsider = User(name="Other", email="other@example.com", password_hash="x", role=Role.EMPLOYEE)
    db.add_all([admin, manager, worker, outsider]); db.flush()
    department = Department(name="Engineering", manager_id=manager.id, created_by=admin.id)
    db.add(department); db.flush()
    db.add_all([
        Employee(employee_number="E1", user_id=manager.id, department_id=department.id, job_title="Manager", hired_on=date.today(), created_by=admin.id, updated_by=admin.id),
        Employee(employee_number="E2", user_id=worker.id, department_id=department.id, job_title="Engineer", hired_on=date.today(), created_by=admin.id, updated_by=admin.id),
        Employee(employee_number="E3", user_id=outsider.id, department_id=department.id, job_title="Engineer", hired_on=date.today(), created_by=admin.id, updated_by=admin.id),
    ])
    db.commit()
    return admin, manager, worker, outsider


def test_prevents_duplicate_clock_in(db):
    _admin, _manager, worker, _outsider = setup_people(db)
    service = AttendanceService(db)
    now = datetime(2026, 10, 6, 9, tzinfo=timezone.utc)
    service.clock_in(worker, None, now)
    with pytest.raises(HTTPException) as error:
        service.clock_in(worker, None, now + timedelta(minutes=1))
    assert error.value.status_code == 409


def test_clock_out_is_owner_protected(db):
    _admin, _manager, worker, outsider = setup_people(db)
    service = AttendanceService(db)
    now = datetime(2026, 10, 6, 9, tzinfo=timezone.utc)
    record = service.clock_in(worker, None, now)
    with pytest.raises(HTTPException) as error:
        service.clock_out(record.id, outsider, None, now + timedelta(hours=8))
    assert error.value.status_code == 403


def test_manager_daily_report_calculates_hours(db):
    _admin, manager, worker, _outsider = setup_people(db)
    service = AttendanceService(db)
    now = datetime(2026, 10, 6, 9, tzinfo=timezone.utc)
    record = service.clock_in(worker, None, now)
    service.clock_out(record.id, worker, None, now + timedelta(hours=8))
    report = service.daily_report(manager, now.date())
    assert report["completed_records"] == 1
    assert report["total_hours"] == 8

