CREATE TABLE users (id BIGSERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, name VARCHAR(120) NOT NULL, role VARCHAR(20) NOT NULL CHECK (role IN ('ADMIN','MANAGER','EMPLOYEE')), is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX users_email_idx ON users(email);
CREATE TABLE auth_sessions (id VARCHAR(36) PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX auth_sessions_user_idx ON auth_sessions(user_id);
CREATE TABLE departments (id BIGSERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL UNIQUE, manager_id BIGINT REFERENCES users(id) ON DELETE SET NULL, created_by BIGINT NOT NULL REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX departments_manager_idx ON departments(manager_id);
CREATE TABLE employees (id BIGSERIAL PRIMARY KEY, employee_number VARCHAR(30) NOT NULL UNIQUE, user_id BIGINT NOT NULL UNIQUE REFERENCES users(id), department_id BIGINT NOT NULL REFERENCES departments(id), job_title VARCHAR(120) NOT NULL, hired_on DATE NOT NULL, created_by BIGINT NOT NULL REFERENCES users(id), updated_by BIGINT NOT NULL REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX employees_department_idx ON employees(department_id);
CREATE TABLE attendance_records (id BIGSERIAL PRIMARY KEY, employee_id BIGINT NOT NULL REFERENCES employees(id) ON DELETE CASCADE, work_date DATE NOT NULL, clock_in TIMESTAMPTZ NOT NULL, clock_out TIMESTAMPTZ, clock_in_note VARCHAR(250), clock_out_note VARCHAR(250), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(employee_id, work_date), CHECK(clock_out IS NULL OR clock_out > clock_in));
CREATE INDEX attendance_date_employee_idx ON attendance_records(work_date, employee_id);

