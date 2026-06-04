# Migrations

This directory is the home for database migration scripts used to keep the PostgreSQL schema in sync with the SQLAlchemy model definitions.

Migration strategy:

- Use Alembic for versioned migrations.
- Keep a single source of truth in `app/database/models/models.py`.
- Create an initial revision for the baseline schema:
  - `alembic revision --autogenerate -m "initial store intelligence schema"`
- For changes, add a new revision and review the generated SQL before applying.
- Apply migrations with `alembic upgrade head` in development and deployment.
- Store migration scripts under this directory so schema history is traceable.

Recommended table evolution pattern:

1. Add or modify SQLAlchemy models.
2. Generate a new Alembic revision.
3. Review the migration script for safe DDL changes.
4. Run the migration locally and validate data.
5. Push the migration script together with the code changes.
