# LifeOS V1 Backend

A robust, production-ready backend system for LifeOS V1 — a behavioral enforcement and tracking system. Built primarily with FastAPI and an asynchronous SQLite database (migratable to Postgres later).

## Key Setup Instructions

1. **Virtual Environment**: Initialize it via `python -m venv venv` and activate it.
2. **Install Dependencies**: Run `pip install -r requirements.txt`.
3. **Database Migrations**: Apply models via `alembic upgrade head`.

## Running Server

Run the local development server:
```bash
uvicorn app.main:app --reload
```

## Running Tests

Execute the comprehensive test suite to validate scoring and auth processes:
```bash
pytest
```

## Features

Please refer to [FEATURES.md](./FEATURES.md).

## Swagger URLs

Once the server is running, you can access Auto-generated Swagger Docs at:
* **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
* **[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)**
