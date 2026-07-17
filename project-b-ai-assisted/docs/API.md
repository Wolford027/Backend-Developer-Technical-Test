# API Reference

Base URL: `http://localhost:8000`

Interactive docs are generated from the code and served at
[`/docs`](http://localhost:8000/docs) (Swagger) and [`/redoc`](http://localhost:8000/redoc)
while the server runs. This file is the narrative version.

---

## Authentication

Management endpoints require an API key in the `X-API-Key` header. **Redirects are public**
— that's the whole point of a short link.

```
X-API-Key: <your key>
```

Mint a key with `python seed_key.py "my-laptop"` (see [SETUP.md](SETUP.md)). The raw key is
shown once and stored only as a SHA-256 hash, so it cannot be recovered — mint a new one if
you lose it.

A key **owns** the links it creates. `GET /api/links` and the stats endpoint only ever
return that key's links. Two keys shortening the same URL get two different codes, so their
click counts never mix.

Missing and invalid keys both return an identical `401`. That's deliberate: a distinct
"that key doesn't exist" message would confirm which keys are real.

---

## Endpoints

### `POST /api/links` — shorten a URL

**Auth required.**

```jsonc
// Request
{
  "url": "https://example.com/a/very/long/path",
  "expires_in_days": 7        // optional; omit or null = never expires
}
```

```jsonc
// 201 Created
{
  "code": "aB3xK9",
  "short_url": "http://localhost:8000/aB3xK9",
  "long_url": "https://example.com/a/very/long/path",
  "click_count": 0,
  "created_at": "2026-07-17T15:08:00",
  "expires_at": "2026-07-24T15:08:00"
}
```

| Status | Meaning |
|---|---|
| `201` | A new link was created. |
| `200` | **You already shortened this URL** — the existing code is returned, nothing was created. |
| `401` | Missing or invalid API key. |
| `422` | The URL is invalid (see [URL rules](#url-rules)). |

**On the 200:** posting the same URL twice with the same key is idempotent — you get the
original code back. Returning `201` would claim a link was created when it wasn't. Note
dedup is scoped to *your* key, and expired links are never reused (you get a fresh code
instead of a dead one).

```bash
curl -X POST localhost:8000/api/links \
  -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com"}'
```

---

### `GET /{code}` — the redirect

**Public. No API key.**

```bash
curl -i localhost:8000/aB3xK9
```

```
HTTP/1.1 307 Temporary Redirect
location: https://example.com/a/very/long/path
cache-control: no-store, max-age=0
```

| Status | Meaning |
|---|---|
| `307` | Redirecting. The click was counted. |
| `404` | No such code — **it never existed**. |
| `410` | The code existed but **has expired**. |

**Why 307 and not 301:** a `301 Moved Permanently` is cached by the browser indefinitely,
so every click after the first would never reach the server and the click count would
silently stop incrementing. `307` plus `no-store` keeps every click observable. If you fork
this and "optimize" the redirect to a 301, you will break click tracking and nothing will
appear to be wrong.

**Why 404 vs 410:** "this link never existed" and "this link died" are different facts, and
which one it is decides what you do next — check the typo, or ask for a fresh link.

Failed redirects (`404`/`410`) do **not** increment any counter.

---

### `GET /api/links` — your links

**Auth required.** Returns the calling key's links, newest first. An empty list is a
normal, successful response — a new key legitimately has no links.

```jsonc
// 200 OK
[
  {
    "code": "aB3xK9",
    "short_url": "http://localhost:8000/aB3xK9",
    "long_url": "https://example.com/a/very/long/path",
    "click_count": 42,
    "created_at": "2026-07-17T15:08:00",
    "expires_at": null
  }
]
```

---

### `GET /api/links/{code}/stats` — click count

**Auth required**, and scoped to links you own.

```jsonc
// 200 OK
{
  "code": "aB3xK9",
  "short_url": "http://localhost:8000/aB3xK9",
  "long_url": "https://example.com/a/very/long/path",
  "click_count": 42,
  "created_at": "2026-07-17T15:08:00",
  "expires_at": null,
  "is_expired": false
}
```

| Status | Meaning |
|---|---|
| `200` | — |
| `401` | Missing or invalid API key. |
| `404` | No such code, **or it belongs to another key**. |

Asking for someone else's code returns `404`, not `403`. `403` would confirm the code
exists, letting anyone with a key probe which codes are real.

---

### `GET /api/health`

**Public.** Returns `{"status": "ok"}`.

---

## URL rules

| Rule | Why |
|---|---|
| Scheme must be `http` or `https` | `javascript:alert(1)` and `data:text/html,...` are *valid URLs*. We hand this string to a browser, so accepting one would make every click on that link execute attacker script — stored XSS. Enforced as an allowlist; a blocklist is only as complete as the last scheme someone thought of. |
| Max 2048 characters | Bounds storage and matches practical browser limits. |
| `expires_in_days` between 1 and 3650 | A zero or negative TTL would create a link that's born dead. |

Rejections come back as `422` with a `detail` explaining which rule failed.

---

## Errors

Every error is a JSON object with a `detail` string:

```json
{ "detail": "This short link has expired" }
```

`422` is the exception — FastAPI returns Pydantic's structured format, an array of objects
each with a `msg`:

```json
{ "detail": [{ "type": "url_scheme", "loc": ["body", "url"], "msg": "URL scheme should be 'http' or 'https'" }] }
```

The frontend's `lib/api.ts` normalizes both shapes into a single `ApiError`.

### Status codes at a glance

| Code | Meaning |
|---|---|
| `200` | OK, or "this URL was already shortened — here's the existing code" |
| `201` | Link created |
| `307` | Redirecting (click counted) |
| `401` | Missing or invalid API key |
| `404` | Code not found, or not yours |
| `410` | Code expired |
| `422` | Invalid URL or TTL |
