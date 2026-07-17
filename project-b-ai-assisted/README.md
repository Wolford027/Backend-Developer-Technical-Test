# URL Shortener

Shorten long URLs, redirect visitors, count the clicks.

FastAPI + SQLite backend, Next.js + React frontend, 44 tests.

```bash
# backend
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
python seed_key.py "my-laptop"        # prints an API key, once

# frontend (second terminal)
cd frontend && npm install && npm run dev
```

Then open <http://localhost:3000> and paste the key.
Full instructions: **[docs/SETUP.md](docs/SETUP.md)**.

---

## Docs

| | |
|---|---|
| **[docs/2026-07-17-url-shortener-design.md](docs/2026-07-17-url-shortener-design.md)** | The planning doc — how I thought before coding: requirements, alternatives rejected, tradeoffs accepted. |
| **[docs/API.md](docs/API.md)** | API reference. (Live Swagger at `/docs` when running.) |
| **[docs/SETUP.md](docs/SETUP.md)** | Setup, config, troubleshooting. |
| **[prompts/](prompts/)** | Full AI session transcript, and which model I used and why. |

## What it does

| | |
|---|---|
| `POST /api/links` | Shorten a URL. **Auth required.** |
| `GET /{code}` | Redirect. **Public.** |
| `GET /api/links` | Your links. **Auth required.** |
| `GET /api/links/{code}/stats` | Click count. **Auth required.** |

API keys **own** their links: the dashboard and stats only ever show links created with the
calling key.

## Four decisions worth knowing

**Redirects are `307`, not `301`.** A 301 is cached by the browser forever, so every click
after the first never reaches the server — the redirect keeps working while the click
counter silently stops. This is the failure mode that looks like success.

**Expired is `410`, missing is `404`.** "This link died" and "this link never existed" are
different facts, and which one it is decides whether you check your typo or ask for a new
link.

**Codes are random base62, not encoded row ids.** Encoding the id gives shorter codes and
zero collisions, but makes every link enumerable — count 1, 2, 3 and scrape the database.

**Clicks increment in SQL, not Python.** `click_count = click_count + 1` is atomic;
`link.click_count += 1` loses concurrent clicks and looks perfectly fine in testing.

The reasoning behind each, plus the alternatives rejected, is in the
[design doc](docs/2026-07-17-url-shortener-design.md).

## Tests

```bash
pytest        # from this directory -> 44 passed
```

Meaningful over numerous — each one targets a way this can actually break: the auth
boundary, cross-key data leaks, duplicate URLs, `javascript:` payloads, expiry, click
counting, and the code-collision retry that 57 billion codes make otherwise unreachable.

They were also **mutation tested** — the code was deliberately broken ten ways to confirm
the tests actually catch bugs rather than merely passing. That found a real defect; see
[prompts/README.md](prompts/README.md).

## Stack

| | |
|---|---|
| Backend | FastAPI, SQLAlchemy, Pydantic, SQLite, pytest |
| Frontend | Next.js (App Router), React, TypeScript, CSS Modules |
| Built with | Claude Opus 4.8 via Claude Code — see [prompts/](prompts/) |
