# Public marketplace API

All routes are unauthenticated and are relative to `/api/v1`.

## Service categories

`GET /public/categories?q=<text>&parentId=<uuid>&limit=100`

Returns active categories only, ordered by `sortOrder`, name, and ID. The optional `q` searches category name and description. The optional `parentId` limits results to direct children of that category.

```json
{
  "data": {
    "items": [
      {
        "id": "category-uuid",
        "slug": "electrical",
        "name": "Electrical",
        "description": "Electrical repairs",
        "parentId": null,
        "sortOrder": 1
      }
    ],
    "nextCursor": null
  }
}
```

## Provider directory

`GET /public/providers?q=<text>&category=<slug-or-uuid>&city=<city>&state=<state>&limit=20&cursor=<opaque>`

- `q` searches provider display name, headline, and bio.
- `category` accepts an active category slug or UUID.
- `city` and `state` are case-insensitive exact matches.
- `limit` defaults to 20 and is restricted to 1-50.
- `cursor` is an opaque keyset cursor returned by the previous page.
- Results are ordered by provider display name and stable user ID.
- Only active accounts with the provider role and an existing provider profile are listed.

Response:

```json
{
  "data": {
    "items": [
      {
        "id": "provider-user-uuid",
        "displayName": "Ada Example",
        "headline": "Licensed electrician",
        "bio": "Residential electrical repairs.",
        "avatarUrl": "https://example.com/provider.jpg",
        "category": { "id": "category-uuid", "name": "Electrical" },
        "serviceAreas": [{ "city": "Port Harcourt" }],
        "hourlyRate": { "amount": 6500, "currency": "NGN", "unit": "hour" }
      }
    ],
    "nextCursor": null
  }
}
```

Fields without stored, approved values are omitted. The current schema does not contain provider service records, availability, verification decisions, public credentials, or eligible published reviews. The API therefore does not fabricate or return those fields. It also never returns account email, phone, identity evidence, session data, or password hashes.

## Public provider profile

`GET /public/providers/{providerId}`

Returns the same public fields as the directory item in a `data` envelope. Unknown, inactive, non-provider, or profile-less accounts return 404 with the same public message so private account state is not disclosed.

## Errors

- `404`: provider profile is not publicly available.
- `422`: invalid UUID, query parameter, or pagination cursor.
- Empty successful lists return `items: []` and `nextCursor: null`.

## Explicitly not implemented in this phase

The customer frontend also proposes `GET /public/services` and public review endpoints. The current backend schema has no provider-service or review persistence model, and this phase issue does not define their lifecycle or publication rules. Those endpoints must be implemented with the corresponding service/review phases, not backed by invented or sample data.
