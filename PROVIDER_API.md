# Provider API

All routes use the `/api/v1` prefix and require an authenticated account with role `provider`, except where stated otherwise. Mutations require the session CSRF token in `X-CSRF-Token`. The server derives provider identity from the session; clients must never submit a trusted provider ID.

All successful responses use the `{ "data": ... }` envelope. Errors use the common FastAPI error detail containing `code` and `message`.

## Provider profile

- `GET /provider/me`: read the authenticated provider's profile, account email/phone, service area, and active service listings.
- `PATCH /provider/me`: update `displayName`, `phone`, `headline`, `bio`, `serviceAreaCity`, and `serviceAreaState`.

Email and verification state are account-owned and read-only here. A street address is not stored or returned by this provider profile API.

## Service listings

- `GET /provider/me/services`: returns `catalogue` and the provider's `items`.
- `POST /provider/me/services`: `{ "serviceId": "uuid", "description": "...", "pricingMode": "from|fixed|quote", "price": 15000 }`.
- `PATCH /provider/me/services/{listingId}`: updates description and/or pricing mode/price.
- `DELETE /provider/me/services/{listingId}`: removes only a listing owned by the authenticated provider.

Prices in request/response display fields are decimal NGN. The database stores integer kobo. `quote` listings have no price; `from` and `fixed` listings require a positive price. A catalogue service can be listed once per provider.

## Availability

- `GET /provider/me/availability`
- `PUT /provider/me/availability`

The PUT replaces the provider's weekly schedule:

```json
{
  "isAvailable": true,
  "timezone": "Africa/Lagos",
  "schedule": [
    { "weekday": 0, "enabled": true, "start": "09:00", "end": "17:00" },
    { "weekday": 1, "enabled": false }
  ]
}
```

Weekdays use ISO-style numbering: Monday 0 through Sunday 6. Times are local to the supplied IANA timezone. Overnight ranges are not supported. An unavailable provider receives no new job opportunities; saved schedule hours are retained.

## Job discovery

- `GET /provider/jobs`: supports `search`, `category` (category UUID or slug), `location`, `minBudget`, `maxBudget`, `sort` (`newest`, `budget-low`, `budget-high`), `limit`, and `cursor`.
- `GET /provider/jobs/{jobId}`: reads one eligible open job.

Only jobs in `AWAITING_BIDS` matching at least one active provider service category are returned. An unavailable provider receives an empty result. Before award, location is limited to the customer's saved city/state. The customer's exact service-location text, name, phone, email, and private notes are not exposed.

Budget filters and displayed amounts are NGN; persisted values remain integer kobo. Pagination cursors are opaque and bound to the selected sort order.

## Bids

- `GET /provider/me/bids?limit=50`
- `POST /provider/jobs/{jobId}/bids`

Request:

```json
{
  "price": 24500,
  "currency": "NGN",
  "message": "I will inspect the joint and repair the leak.",
  "proposedSchedule": "2026-12-02T10:30"
}
```

A proposed local date/time without an offset is interpreted in `Africa/Lagos` and stored in UTC. An offset-aware ISO timestamp is also accepted. One bid per provider/job is enforced; a repeated submission returns 409. The job is locked and rechecked at submission time. A bid includes the persisted ID and server status.

## Accepted jobs and progress

- `GET /provider/me/jobs?status=...`
- `PATCH /provider/me/jobs/{jobId}/progress`

The current customer acceptance flow moves the selected job directly to `IN_PROGRESS`. The provider can request `COMPLETE` only for an accepted job currently in that state:

```json
{ "transition": "COMPLETE", "expectedUpdatedAt": "2026-11-27T10:00:00+00:00" }
```

The server checks ownership, current state, and the expected update timestamp while locking the job. A stale timestamp returns 409. The response includes the persisted job and allowed transitions.

## Earnings

- `GET /provider/me/earnings?limit=50`

The endpoint reports pending bids as `estimated` amounts and accepted jobs as `agreed` amounts. No paid amount or payment record is fabricated. The response explicitly reports `paidRecordsAvailable: false` and `payoutStatus: "UNAVAILABLE"` because payment processing, payout setup, and withdrawals are not part of this phase.

## Excluded

In-app messaging is excluded by the frontend product rules. Payment collection, payout setup, bank-account management, and withdrawals require a separately approved payment-provider design and are not implemented by this API.
