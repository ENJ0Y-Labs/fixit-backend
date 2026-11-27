# Changelog

All notable changes to this project are documented here.

## [0.4.0] - 2026-11-27

### Added
- Public active service-category discovery with text and parent-category filtering.
- Public provider directory with search, category and location filters, and cursor pagination.
- Public provider profiles with a restricted allowlist of profile fields.
- Public marketplace API documentation and privacy/pagination tests.

### Security
- Conceal inactive, non-provider, and profile-less accounts from public provider lookup.
- Exclude private account, authentication, and verification evidence from public responses.

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
