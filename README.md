# FixIt Backend

Python REST API for the FixIt marketplace, serving the Customer, Provider, and Admin applications.

## Technology

- Python 3.12+
- FastAPI
- PostgreSQL 16+
- SQLAlchemy 2
- Alembic
- Pydantic Settings
- Pytest and HTTPX
- Ruff

## Local setup

### 1. Create and activate a virtual environment

Windows CMD:
```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate
```

PowerShell:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Start PostgreSQL
Create a PostgreSQL database named `fixit`. The default local connection is:
```text
postgresql+psycopg://postgres:postgres@localhost:5432/fixit
```
Use your own local credentials and database name where needed.

### 4. Configure environment variables
Copy `.env.example` to `.env` and update `DATABASE_URL`.

Windows CMD:
```cmd
copy .env.example .env
```
macOS/Linux:
```bash
cp .env.example .env
```
Never commit `.env` or production secrets.

### 5. Apply database migrations
```bash
alembic upgrade head
```
To roll back the initial migration:
```bash
alembic downgrade base
```

### 6. Run the API
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/api/v1/health
- Interactive API docs: http://127.0.0.1:8000/docs

### 7. Run checks
The test suite expects the PostgreSQL database configured by `DATABASE_URL` to have the latest migration applied.
```bash
ruff check .
ruff format --check .
alembic upgrade head
pytest -q
```

## API contracts

- [Public marketplace API](./PUBLIC_MARKETPLACE_API.md): unauthenticated category and provider discovery, filtering, pagination, and public-field rules.
- [Customer API](./CUSTOMER_API.md): customer profiles, job lifecycle, bid review and acceptance, and provider favorites.

## Database schema

- `users`: canonical account identity, unique email/phone, password hash, role, and active state.
- `customer_profiles`, `provider_profiles`, and `admin_profiles`: one-to-one role-specific profile data.
- `service_categories`: hierarchical categories with unique slugs and active/sort ordering.
- `jobs`: customer-owned service requests, preferred schedule/location, status, and integer-kobo budget/agreed price.
- `bids`: provider offers linked to jobs, with integer-kobo amounts and acceptance status.
- `customer_favorites`: unique customer/provider favorites.

Profile rows use `user_id` as both primary key and foreign key. Deleting a user cascades to their profile and owned records. Customer job, bid, and favorite ownership is enforced by the API and database constraints. The customer migration seeds the categories currently shown by the customer job form.

Canonical roles are `customer`, `provider`, and `admin`. Authentication, public marketplace, and customer APIs are implemented. Provider bid submission and the remaining provider/admin workflows are separate phases.

## Project structure

```text
app/
  api/v1/       Versioned API routes
  core/         Application configuration
  db/           SQLAlchemy base and session factory
  models/       Database models
  main.py       FastAPI application entry point
migrations/     Alembic environment and revisions
tests/          Automated tests
.env.example    Environment variable template
alembic.ini     Alembic configuration
pyproject.toml  Project and tool configuration
requirements.txt
```
