from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AttendanceRecord, Department, Employee, User


class AttendanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_actor(self, actor: User, start: date, end: date, employee_id: int | None, page: int, limit: int):
        query = select(AttendanceRecord).join(Employee)
        count = select(func.count()).select_from(AttendanceRecord).join(Employee)
        conditions = [AttendanceRecord.work_date.between(start, end)]
        if actor.role.value == "EMPLOYEE":
            conditions.append(Employee.user_id == actor.id)
        elif actor.role.value == "MANAGER":
            conditions.append(Employee.department_id.in_(select(Department.id).where(Department.manager_id == actor.id)))
        if employee_id:
            conditions.append(AttendanceRecord.employee_id == employee_id)
        items = self.db.scalars(query.where(*conditions).order_by(AttendanceRecord.work_date.desc(), AttendanceRecord.id.desc()).offset((page - 1) * limit).limit(limit)).all()
        return list(items), self.db.scalar(count.where(*conditions)) or 0

