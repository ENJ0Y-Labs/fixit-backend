# Authentication API (v1)

All endpoints are prefixed with `/api/v1`. Success responses use `{"data": ...}`; FastAPI validation and HTTP errors use the standard `detail` payload.

## Registration

`POST /auth/register`

Body: `{"name":"Ada Example","email":"ada@example.com","phone":"+2348012345678","password":"at-least-12-characters","role":"customer"}`

Only `customer` and `provider` are accepted. Phone is optional and is not verified in this phase. Registration creates the matching profile and sends an email verification token. It does not create an authenticated session.

## Login, identity, logout

- `POST /auth/login`: `{"email":"ada@example.com","password":"..."}`. Sets HttpOnly `fixit_session` and readable `fixit_csrf` cookies.
- `GET /auth/me`: returns the current user, role, email verification state, and role capability.
- `POST /auth/logout`: revokes the current server-side session and clears cookies.

Session lifetime defaults to seven days. Password reset revokes all active sessions.

Browser state-changing requests authenticated by the session cookie must send `X-CSRF-Token` equal to the `fixit_csrf` cookie. Native clients do not send browser Origin headers and rely on the platform cookie jar; do not expose browser cookies to JavaScript except the dedicated CSRF cookie.

## Password recovery and email verification

- `POST /auth/password/forgot`: `{"email":"..."}`. Always returns a generic response.
- `POST /auth/password/reset`: `{"token":"...","password":"at-least-12-characters"}`.
- `POST /auth/verification/request`: `{"email":"..."}`. Always returns a generic response.
- `POST /auth/verification/confirm`: `{"token":"..."}`.

Tokens are random, single-use, expire after 30 minutes, and only SHA-256 digests are stored. Configure Mailgun with `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, and `MAILGUN_FROM`. In development/test, missing credentials suppress delivery and log only the recipient.

## Admin provisioning

There is intentionally no public admin registration endpoint. Provision admin accounts through a controlled operator workflow; never expose this capability to the public API.

## Configuration

See `.env.example`. Set `COOKIE_SECURE=true` behind HTTPS in production. Configure exact CORS origins at the deployment layer before exposing browser sessions.
