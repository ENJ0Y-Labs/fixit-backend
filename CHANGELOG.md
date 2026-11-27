# Changelog

All notable changes to this project are documented here.

## [0.6.0] - 2026-11-27

### Added
- Provider profile read/update with server-side role and ownership enforcement.
- Provider service listing management against the canonical service catalogue.
- Persisted weekly availability schedules using an explicit IANA timezone.
- Eligible open-job discovery with privacy-safe location fields, filters, sorting, and cursor pagination.
- Provider bid submission and bid history with duplicate protection and optional proposed schedules.
- Accepted-job listing and optimistic-concurrency checks for completion transitions.
- Provider earnings summaries that separate pending quotes from agreed job amounts.

### Security
- Provider endpoints require an authenticated provider session and CSRF validation for mutations.
- Job discovery hides customer contact details and exact service addresses before a bid is accepted.
- Provider resource reads and mutations are scoped to the authenticated provider.

### Notes
- Payment records, payouts, withdrawals, and messaging remain outside this phase.

## [0.5.0] - 2026-11-27

### Added
- Database-backed service catalogue linked to service categories.
- Starter catalogue records for plumbing, electrical, cleaning, carpentry, and painting.
- Public service discovery with text/category filters and cursor pagination.
- Provider service-listing persistence linked to canonical catalogue service IDs.
- Public provider service data and provider directory filtering by service ID.

### Security
- Hide inactive catalogue services, inactive categories, and inactive provider listings from public discovery.

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
