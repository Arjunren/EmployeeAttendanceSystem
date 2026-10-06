# Employee Attendance System

## Overview

A production-structured REST API for employee profiles, departments, daily clock-in/clock-out records, and attendance reporting.

## Features

- Login, revocable logout, and admin/manager/employee roles
- Admin-managed departments and employee accounts
- Atomic daily clock-in with duplicate prevention and row-locked clock-out
- Employee ownership, manager department scope, search, pagination, date filtering, dashboard, and daily hour reports
- Audit timestamps, PostgreSQL migrations, development seed, Docker, tests, dependency audit, and CI

## Technology Stack

Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, PostgreSQL 17, PyJWT, Argon2, pytest, Ruff, pip-audit, Docker.

## Requirements

Python 3.12+ and PostgreSQL 15+, or Docker with Compose.

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
copy .env.example .env
```

## Environment Variables

Set required `DATABASE_URL` and a random `JWT_SECRET` of at least 32 characters. Optional: `JWT_EXPIRY_MINUTES` and comma-separated `ALLOWED_ORIGINS`. Examples are local-only.

## Database Setup

```bash
python -m app.migrate
python -m app.seed
```

Docker alternative: `docker compose up -d db`, then run `docker compose --profile tools run --rm migrate` and `docker compose --profile tools run --rm seed`.

## Running the Application

```bash
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`. With Docker, run `docker compose up --build api` after migration.

## Running Tests

```bash
ruff check .
pytest -q
pip-audit
```

## Default Development Accounts

Seed-only local accounts: admin `admin@example.com` / `AdminPassword123!`; manager `manager@example.com` / `ManagerPassword123!`; employee `employee@example.com` / `EmployeePassword123!`. Change these outside a disposable development environment.

## API Endpoints

`POST /api/auth/login`, `POST /api/auth/logout`; `GET/POST /api/departments`; `GET/POST /api/employees`; `GET /api/attendance`; `POST /api/attendance/clock-in`; `PATCH /api/attendance/{id}/clock-out`; `GET /api/reports/daily`; `GET /api/dashboard`; `GET /health`.

## Folder Structure

`app/` contains the HTTP, schema, service, repository, model, auth, and configuration layers. `migrations/` owns PostgreSQL schema changes. `tests/` contains isolated business-rule tests. `.github/workflows/` runs PostgreSQL CI.

## Architecture

Thin FastAPI routes delegate rules to services; repositories build scoped queries; schemas define allowed fields; SQLAlchemy models and migrations enforce relational invariants.

## Security Notes

Argon2 password hashing, revocable short-lived JWT sessions, rate-limited login with timing equalization, server-side role and department authorization, object ownership, parameterized queries, row locking, unique constraints, bounded inputs, allow-listed CORS, generic server errors, and no password-hash exposure.

## Known Limitations

Attendance uses the application server's UTC date; organizations needing local shifts should add a per-worksite timezone and overnight-shift rules. The login limiter is per process. Payroll, leave, biometrics, geofencing, approval corrections, and immutable external audit storage are intentionally outside this portfolio scope.
