from datetime import date

from sqlalchemy import select

from app.auth import hash_password
from app.database import SessionLocal
from app.models import Department, Employee, Role, User


def make_user(db, name: str, email: str, password: str, role: Role) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(name=name, email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()
    return user


def main() -> None:
    with SessionLocal() as db:
        admin = make_user(db, "Development Admin", "admin@example.com", "AdminPassword123!", Role.ADMIN)
        manager = make_user(db, "Development Manager", "manager@example.com", "ManagerPassword123!", Role.MANAGER)
        employee_user = make_user(db, "Development Employee", "employee@example.com", "EmployeePassword123!", Role.EMPLOYEE)
        department = db.scalar(select(Department).where(Department.name == "Engineering"))
        if department is None:
            department = Department(name="Engineering", manager_id=manager.id, created_by=admin.id)
            db.add(department)
            db.flush()
        for number, user, title in (("EMP-001", manager, "Engineering Manager"), ("EMP-002", employee_user, "Software Engineer")):
            if db.scalar(select(Employee).where(Employee.user_id == user.id)) is None:
                db.add(Employee(employee_number=number, user_id=user.id, department_id=department.id, job_title=title, hired_on=date(2026, 1, 1), created_by=admin.id, updated_by=admin.id))
        db.commit()
    print("development seed complete")


if __name__ == "__main__":
    main()

