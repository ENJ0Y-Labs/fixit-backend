# Customer API contract

All routes are relative to `/api/v1` and require a valid session cookie. Customer routes enforce the `customer` role and scope every job/favorite query to the authenticated user. Mutating requests use the existing CSRF cookie/header validation when an Origin header is supplied.

## Profile

- `GET /customer/me`
- `PATCH /customer/me`

Editable fields: `displayName`, `defaultCity`, and `defaultState`. Email, phone, role, verification and account status are read-only. Responses use `{ "data": { ... } }`.

## Jobs

- `GET /customer/me/jobs?limit=50&cursor=<opaque>`
- `POST /customer/me/jobs`
- `GET /customer/me/jobs/{jobId}`
- `PATCH /customer/me/jobs/{jobId}`
- `POST /customer/me/jobs/{jobId}/cancel`
- `GET /customer/me/jobs/{jobId}/bids`
- `POST /customer/me/jobs/{jobId}/bids/{bidId}/accept`

Create/update fields: `title`, `category` (active category UUID, slug, or case-insensitive category name), `description`, `urgency` (`LOW`, `NORMAL`, `HIGH`, `URGENT`; the current customer form's `normal`, `urgent`, and `asap` values are normalized), `preferredDate`/`date`, `preferredTime`/`time`, `serviceLocation`/`location`, and `budget`. The current customer form submits budget in naira as a decimal number with at most two decimal places. The API converts it to integer kobo before persistence; responses include `budget` as a two-decimal naira string and `budgetKobo` as the canonical integer. No floating-point amount is stored.

New jobs start as `AWAITING_BIDS`. Only jobs in that state can be edited or cancelled. The backend exposes `cancel` and `edit` in `availableActions` only for that state. Cancellation changes the status to `CANCELLED`.

List responses use `{ "data": { "items": [], "nextCursor": null } }`. Cursor pagination sorts by creation time and UUID descending. Single-resource responses use `{ "data": { ... } }`.

## Bids and acceptance

Bids are stored in the canonical `bids` table with integer `amount_kobo`, provider identity, message, estimated days, and `PENDING`, `ACCEPTED`, or `DECLINED` status. The customer can only list bids for a job they own. A bid can be accepted only while its job is `AWAITING_BIDS` and the bid is pending and belongs to that job.

Acceptance runs in a transaction while locking the job row: the job becomes `IN_PROGRESS`, the selected bid becomes `ACCEPTED`, the provider and agreed kobo amount are recorded, and competing pending bids become `DECLINED`. This prevents accepting multiple bids for one job. Provider bid submission is intentionally not part of this customer phase; the provider phase must write to this same bid contract.

## Favorites

- `GET /customer/me/favorites`
- `PUT /customer/me/favorites/{providerId}`
- `DELETE /customer/me/favorites/{providerId}`

Only active provider accounts with a provider profile can be favorited. Repeated PUT requests are idempotent. DELETE succeeds when the favorite is already absent. The database enforces one favorite per customer/provider pair.

## Errors and privacy

Errors use FastAPI's existing `detail.code` and `detail.message` format. Not-found responses intentionally conceal resources that do not belong to the current customer. No customer or provider contact details are returned in job, bid, or favorite summaries. Payment, escrow, uploads, messaging, notifications and reviews are outside this phase and are not implied by these responses.
