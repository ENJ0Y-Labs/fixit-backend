# Changelog

All notable changes to this project are documented here.

## [0.3.0] - 2026-11-27

### Added
- Customer and provider registration with Argon2id password hashing.
- Persistent, revocable PostgreSQL sessions and HttpOnly session cookies.
- Login, logout, and authenticated identity endpoint.
- Single-use email verification and password reset tokens stored as hashes.
- Mailgun email adapter with safe development/test suppression.
- Operator-only admin provisioning remains the only supported admin creation path.
- Authentication schema migration and configuration examples.

## [0.2.0] - 2026-11-27

### Added
- PostgreSQL connection configuration using SQLAlchemy 2 and psycopg 3.
- Initial user, customer, provider, admin, and service-category models.
- Alembic migration environment and initial schema migration.
- PostgreSQL-backed migration and schema checks in CI.
