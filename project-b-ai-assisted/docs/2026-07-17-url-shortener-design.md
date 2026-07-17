# URL Shortener — Design

**Date:** 2026-07-17
**Status:** Approved, pending implementation plan

This is the thinking that happened before the code. It records what I understood the
requirements to be, the approach I chose, the alternatives I rejected and why, and the
tradeoffs I'm knowingly accepting.

---

## 1. Understanding the requirements

The literal asks, and what each one actually implies:

| Requirement | What it implies beyond the literal reading |
|---|---|
| Create a short URL from a long URL | Needs auth, URL validation, and a collision-safe code generator |
| Redirect endpoint resolves code → original | Must be public, and must stay *observable* so clicks can be counted |
| Stats endpoint returns click count | Counting has to survive concurrent clicks |
| API key auth for creating; redirects public | Two distinct trust zones in one app |
| Persist to SQLite | Single-writer DB; increments belong in SQL, not Python |
| Handle duplicate URLs, invalid URLs, expired/missing codes | Four named edge cases — each gets a test |
| Dashboard of "your created URLs" | "Your" is meaningless unless keys own rows — this drives the schema |

### The requirement that shaped everything else

"A dashboard showing **your** created URLs" and "simple authentication via API key" are in
tension. A single shared key in `.env` satisfies the auth sentence literally, but then
"your URLs" degrades to "all URLs" — there is no *your*. The dashboard requirement only
means something if a key **owns** the links it creates.

So: an `api_keys` table, and `links.api_key_id` as a foreign key. This is the difference
between authentication (who are you?) and authorization (what may you see?). The challenge
only names the first, but the dashboard silently requires the second.

**Tradeoff accepted:** one extra table and a seed script, versus a one-line env var.
Worth it — it's the difference between a demo and a design.

---

## 2. Architecture

Two processes, mirroring `project-a-manual` so the two projects read as one codebase.

```
┌─────────────────┐        fetch + X-API-Key        ┌──────────────────┐
│  Next.js :3000  │ ──────────────────────────────► │  FastAPI :8000   │
│  form + dash    │ ◄────────────────────────────── │                  │
└─────────────────┘          JSON                   │  ┌────────────┐  │
                                                    │  │ SQLite     │  │
   browser ──────── GET /{code} (public) ─────────► │  └────────────┘  │
           ◄─────── 307 → original URL ──────────── └──────────────────┘
```

### Backend module layout

Split by responsibility rather than piling into `main.py`:

| File | Owns | Depends on |
|---|---|---|
| `main.py` | HTTP routes, status codes | everything below |
| `auth.py` | `require_api_key` dependency | `crud`, `database` |
| `crud.py` | data access | `models`, `schemas` |
| `shortcode.py` | base62 code generation | stdlib only |
| `models.py` | SQLAlchemy tables | `database` |
| `schemas.py` | Pydantic request/response + URL validation | stdlib only |
| `database.py` | engine, session, `Base` | — |
| `config.py` | settings (DB path, code length, base URL) | stdlib only |
| `seed_key.py` | CLI to mint an API key | `crud`, `database` |

The rule that makes this worth doing: **`crud.py` never imports FastAPI.** The data layer
is testable without HTTP, and `shortcode.py` is pure — testable without a database. Each
file is small enough to hold in context at once.

---

## 3. Data model

```sql
api_keys
  id          INTEGER PK
  key_hash    TEXT UNIQUE NOT NULL   -- SHA-256, never plaintext
  name        TEXT NOT NULL          -- human label, e.g. "joshua-laptop"
  created_at  DATETIME NOT NULL

links
  id          INTEGER PK
  code        TEXT UNIQUE NOT NULL   -- indexed; the redirect's lookup key
  long_url    TEXT NOT NULL
  api_key_id  INTEGER NOT NULL REFERENCES api_keys(id)
  click_count INTEGER NOT NULL DEFAULT 0
  created_at  DATETIME NOT NULL
  expires_at  DATETIME NULL          -- NULL = never expires
```

**Keys are stored as SHA-256 hashes.** `seed_key.py` prints the raw key once; after that
it's unrecoverable. Same reasoning as password storage: a leaked database shouldn't hand
over working credentials. Costs one line.

Lookup is by hash (`WHERE key_hash = sha256(presented)`) — an indexed exact match, not a
scan over every key doing string comparisons.

On timing: hashing does *not* make the comparison constant-time — the index lookup still
compares bytes. It defuses the attack for a different reason. To exploit a timing signal
on `key_hash`, an attacker would have to submit a candidate whose *SHA-256* shares a
prefix with a stored hash, then work backwards to the key that produced it — i.e. invert
the hash. The comparison isn't constant-time; it's comparing a value the attacker can't
steer.

**Index on `code`** — it's on the hot path (every redirect) and is the only column the
redirect filters by.

---

## 4. Short code generation

**Chosen:** 6 chars of base62 from `secrets.choice`, `UNIQUE` constraint on `code`, retry
on `IntegrityError`.

Alternatives considered:

| Approach | Why not |
|---|---|
| base62-encode the row `id` | Shortest codes, zero collisions — but codes become `1, 2, 3...` → `b, c, d`. Every link is trivially enumerable; anyone can scrape the whole database by counting. Fatal. |
| Hash the long URL, truncate | Dedup falls out for free — but truncating reintroduces collisions with *none* of the randomness benefit, and identical URLs from different keys would collide by design. |
| UUID4 | No collisions in practice, but a 36-char "short" URL is a contradiction. |
| **Random base62 + retry** | Not guessable; 62^6 ≈ 57 billion, so retry is nearly unreachable. |

**Tradeoff:** the retry branch is the least-exercised code in the app, and "nearly
unreachable" is exactly how a latent bug survives to production. So a test **forces** a
collision (monkeypatching the generator to return a known-taken code) rather than hoping.

---

## 5. The redirect — why 307, not 301

This is the decision most likely to be gotten wrong, and it fails *silently*.

**301 Moved Permanently is cached by the browser indefinitely.** After the first click,
subsequent clicks never reach the server. The redirect keeps working perfectly — and the
click counter silently stops moving. The feature breaks in precisely the way that looks
like it works.

**Chosen:** `307 Temporary Redirect` + `Cache-Control: no-store`. Every click reaches the
server and is counted.

**Tradeoff:** 301 is marginally faster for repeat visitors and passes SEO link equity. We
are explicitly trading that away — click tracking is a stated requirement, SEO is not.

### Counting concurrently

```python
# Atomic — the database resolves concurrent clicks.
UPDATE links SET click_count = click_count + 1 WHERE id = ?
```

Not read-modify-write in Python:

```python
link.click_count += 1   # ← two concurrent clicks both read 5, both write 6. One lost.
```

SQLite serializes writers, so the SQL-side increment is safe. The Python version has a
lost-update race that is invisible in single-user testing and shows up only under load.

---

## 6. API surface

| Method | Path | Auth | Success | Notes |
|---|---|---|---|---|
| POST | `/api/links` | ✅ | 201 / **200** | 200 when this key already shortened this URL |
| GET | `/api/links` | ✅ | 200 | only links owned by the calling key |
| GET | `/api/links/{code}/stats` | ✅ | 200 | owner-scoped |
| GET | `/{code}` | ❌ | 307 | public redirect |
| GET | `/api/health` | ❌ | 200 | matches project-a |

### Status codes

| Code | When | Why this code |
|---|---|---|
| 201 | new link created | — |
| 200 | duplicate URL, existing code returned | Nothing was created; 201 would be a lie |
| 307 | redirect | Keeps clicks observable (§5) |
| 401 | key missing or invalid | Both cases identical — revealing "key exists but wrong" leaks key validity |
| 404 | code never existed | — |
| 410 | code existed, has expired | See below |
| 422 | invalid URL | Pydantic's native validation code |

**404 vs 410 is the distinction that matters.** "This link never existed" and "this link
died" are different facts. Collapsing them into 404 throws away the only thing the user
actually needs to know — whether to check their typo or ask for a fresh link.

### Duplicate handling

Dedup is scoped **per key** (`WHERE long_url = ? AND api_key_id = ?`), not global. Two
different keys shortening the same URL get different codes — otherwise key A's clicks
would land in key B's stats, and one tenant's data would leak into another's dashboard.

### Expiry

The request takes a **relative** TTL, the response returns an **absolute** timestamp:

```
POST /api/links  { "url": "...", "expires_in_days": 7 }   # optional, omit = never
  →  201        { "code": "aB3xK9", "expires_at": "2026-07-24T15:08:00Z", ... }
```

Relative in, absolute out. Callers shouldn't have to compute a timestamp (or get the
server's clock skew wrong) to say "a week"; readers shouldn't have to know when a link was
created to work out when it dies. Stored as absolute `expires_at`.

Checked at redirect time (lazy), not by a background sweeper — no scheduler for a feature
this size, and a stale row is harmless as long as it's never served.

---

## 7. URL validation

Pydantic `HttpUrl` gets us syntax. It is **not** sufficient on its own:

```
javascript:alert(document.cookie)   # ← a valid URL. Not a valid destination.
data:text/html,<script>...</script>
file:///etc/passwd
```

We hand `long_url` straight to a browser in a redirect. An unvalidated scheme is a
**stored XSS vector**, not a tidiness issue — anyone who clicks the short link executes
the attacker's script.

**Rules:** scheme must be `http` or `https` (allowlist, not a blocklist of known-bad —
blocklists are always incomplete); max length 2048.

**Explicitly out of scope:** SSRF protection (blocking `localhost` / RFC1918 targets). We
only *redirect* the browser, never fetch the URL server-side, so there's no server-side
request to forge. Noted here so it's visibly a decision rather than an oversight.

---

## 8. Frontend

Single page, three zones: API-key field → shorten form → dashboard table.

**Key handling:** user pastes a key, stored in `localStorage`, sent as `X-API-Key`.
The alternative — `NEXT_PUBLIC_API_KEY` — ships the key in the JS bundle to every visitor.
A `NEXT_PUBLIC_` var is not a secret; treating it as one is worse than not having auth,
because it *looks* secure. localStorage also lets the demo switch keys to show ownership
scoping working.

**Tradeoff:** localStorage is XSS-readable. For a challenge with seeded dev keys this is
fine; production would use an httpOnly cookie or a server-side proxy (considered, rejected
— the proxy layer hides the FastAPI surface this challenge exists to show).

**Every async surface gets four states:** loading, error, empty, populated.

The empty dashboard is the one that gets skipped, and it's the **first thing a reviewer
sees** — a fresh key with no links. If it renders as a bare table header or a flash of
"undefined", that's the first impression.

Errors are specific and actionable: 401 → "Invalid API key", 422 → "That doesn't look
like a valid URL", network failure → "Can't reach the API — is the backend running?".
"Something went wrong" tells the user nothing they didn't already know.

---

## 9. Testing

pytest + `TestClient`, temp SQLite file per test via `get_db` dependency override.
**Tests never touch the dev database** — a test suite that wipes real data gets run once
and then never again.

Meaningful over numerous. Each test targets a way this can actually break:

| Test | Guards against |
|---|---|
| create without key → 401; garbage key → 401 | auth bypass |
| create → redirect 307 → original URL | the core path |
| same URL twice → same code, 200 | duplicate edge case |
| `javascript:` scheme → 422 | stored XSS (§7) |
| unknown code → 404 | missing edge case |
| expired code → 410 | expired edge case, and 410≠404 |
| 3 redirects → stats == 3 | the counter actually counts |
| **key B can't read/stat key A's links** | the authorization boundary |
| forced collision → distinct code | the retry branch that never runs naturally |

The last two matter most. **Ownership isolation fails silently** — everything looks
correct until someone else's data shows up in your dashboard, and no unit test of a single
key ever catches it. And the collision retry is unreachable by chance, so it's only ever
tested if forced.

---

## 10. Deliverables

```
project-b-ai-assisted/
├── backend/     main, auth, crud, models, schemas, shortcode, database, config, seed_key
├── frontend/    Next.js app router — form + dashboard
├── tests/       pytest
├── docs/        this file + API docs + setup guide
└── prompts/     full Claude Code transcript + model rationale
```

## 11. Known tradeoffs, collected

1. **SQLite, single writer** — correct for the brief; Postgres if this ever scaled.
2. **Counter column, no per-click rows** — satisfies "click count"; no time-series
   possible without a migration. Deliberate: the spec says *count*.
3. **localStorage keys** — XSS-readable; acceptable for seeded dev keys (§8).
4. **No rate limiting** — a real shortener needs it (abuse magnet). Out of scope, named
   so it's a decision.
5. **No custom aliases / no delete** — not requested. YAGNI.
6. **Lazy expiry** — expired rows persist until requested. Harmless; never served.
