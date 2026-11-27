# Public marketplace API

All routes are unauthenticated and are relative to `/api/v1`.

## Service categories

`GET /public/categories?q=<text>&parentId=<uuid>&limit=100`

Returns active categories only, ordered by `sortOrder`, name, and ID. The optional `q` searches category name and description. The optional `parentId` limits results to direct children of that category.

## Service catalogue

`GET /public/services?q=<text>&categoryId=<uuid>&limit=20&cursor=<opaque>`

Returns active catalogue services whose parent category is active.

- `q` searches service name and description.
- `categoryId` restricts results to one category.
- `limit` defaults to 20 and is restricted to 1-100.
- `cursor` is an opaque keyset cursor returned by the previous page.
- Results are ordered by service name and stable service ID.

Example:

```json
{
  "data": {
    "items": [
      {
        "id": "service-uuid",
        "slug": "socket-repair",
        "name": "Socket repair",
        "description": "Inspect and repair faulty electrical sockets.",
        "sortOrder": 1,
        "category": {
          "id": "category-uuid",
          "slug": "electrical",
          "name": "Electrical",
          "description": "Electrical installation and repairs",
          "parentId": null,
          "sortOrder": 2
        }
      }
    ],
    "nextCursor": null
  }
}
```

The catalogue is seeded by migration with starter services under Plumbing, Electrical, Cleaning, Carpentry, and Painting. Catalogue rows are database records, not frontend fixtures. Inactive services and services under inactive categories are hidden.

## Provider directory

`GET /public/providers?q=<text>&category=<slug-or-uuid>&serviceId=<uuid>&city=<city>&state=<state>&limit=20&cursor=<opaque>`

- `q` searches provider display name, headline, and bio.
- `category` accepts an active category slug or UUID and filters the provider's primary category.
- `serviceId` filters to providers with an active listing for that active catalogue service.
- `city` and `state` are case-insensitive exact matches.
- `limit` defaults to 20 and is restricted to 1-50.
- `cursor` is an opaque keyset cursor returned by the previous page.
- Results are ordered by provider display name and stable user ID.
- Only active accounts with the provider role and an existing provider profile are listed.

Provider service listing records reference a catalogue service ID. Public profiles and directory results include only active provider listings whose catalogue service and category are active. Prices are persisted as integer kobo and serialized as integer NGN amounts for the provider's current whole-naira pricing inputs. The provider create/update/delete service-listing endpoints belong to the provider functionality phase and are not part of this public discovery API.

## Public provider profile

`GET /public/providers/{providerId}`

Returns the same public fields as the directory item in a `data` envelope, including active catalogue service listings when present. Unknown, inactive, non-provider, or profile-less accounts return 404 with the same public message so private account state is not disclosed.

## Public data rules

Fields without stored, approved values are omitted. The API does not fabricate availability, verification, credentials, ratings, or reviews. It never returns account email, phone, identity evidence, session data, or password hashes.

## Errors

- `404`: provider profile is not publicly available.
- `422`: invalid UUID, query parameter, or pagination cursor.
- Empty successful lists return `items: []` and `nextCursor: null`.
