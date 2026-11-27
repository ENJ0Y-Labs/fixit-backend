# FixIt Backend

Python REST API for the FixIt marketplace, serving the Customer, Provider, and Admin applications.

## Technology

- Python 3.12+
- FastAPI
- Pydantic Settings
- Uvicorn
- Pytest and HTTPX
- Ruff

## Local setup

### 1. Create and activate a virtual environment

Windows CMD:

```cmd
py -3.12 -m venv .venv
.venv\\Scripts\\activate
```

PowerShell:

```powershell
py -3.12 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
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

### 3. Configure environment variables

Copy `.env.example` to `.env` and adjust values for your local environment.

Windows CMD:

```cmd
copy .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Never commit `.env` or production secrets.

### 4. Run the API

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/api/v1/health
- Interactive API docs: http://127.0.0.1:8000/docs

### 5. Run checks

```bash
pytest -q
ruff check .
ruff format --check .
```

## Project structure

```text
app/
  api/v1/       Versioned API routes
  core/         Application configuration
  main.py       FastAPI application entry point
tests/          Automated tests
.env.example    Environment variable template
pyproject.toml  Project and tool configuration
requirements.txt
```

## API versioning

Application endpoints are versioned under `/api/v1`. The root and health endpoints are intentionally small foundation endpoints; feature contracts will be added in later implementation phases.
