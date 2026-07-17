# Setup

Two processes: a FastAPI backend on `:8000` and a Next.js frontend on `:3000`. You need
both running.

**Prerequisites:** Python 3.12+ and Node 20+. (Built and verified on Python 3.14.6 and
Node 24.18.)

---

## 1. Backend

```bash
cd project-b-ai-assisted/backend

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Start it:

```bash
uvicorn main:app --reload --port 8000
```

The SQLite file (`shortener.db`) is created automatically on first run. Check it's alive:

```bash
curl localhost:8000/api/health     # -> {"status":"ok"}
```

Interactive API docs: <http://localhost:8000/docs>

## 2. Mint an API key

Creating links requires a key. Redirects don't.

```bash
# in backend/, with the venv active
python seed_key.py "my-laptop"
```

```
  API key for 'my-laptop' created.

    xK9_aB3mQp7...

  Save it now -- it is not recoverable.
```

**Copy it now.** Only a SHA-256 hash is stored, so there is no way to read it back. Lost a
key? Mint another — they're free, and each one owns its own links.

## 3. Frontend

In a second terminal:

```bash
cd project-b-ai-assisted/frontend
npm install
npm run dev
```

Open <http://localhost:3000>, paste the key from step 2, and shorten something.

**No frontend config needed for local development.** The API location defaults to
`http://localhost:8000` in code, so the two halves find each other out of the box.

If you move the backend somewhere else, point the frontend at it by copying the example
env file and editing it:

```bash
cp .env.example .env.local     # then edit NEXT_PUBLIC_API_URL
```

`.env.local` is git-ignored, which is why a fresh clone doesn't have one.

---

## Running the tests

```bash
cd project-b-ai-assisted
./backend/venv/bin/python -m pytest        # or: pytest, with the venv active
```

```
44 passed
```

Tests run against a throwaway SQLite file in a temp directory, so they never touch
`shortener.db`.

Frontend checks:

```bash
cd frontend
npx tsc --noEmit && npx eslint . && npm run build
```

---

## Configuration

All optional — the defaults work for local development.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./shortener.db` | Where SQLite lives. |
| `BASE_URL` | `http://localhost:8000` | Origin used to build `short_url` in responses. Set this if you deploy, or your short links will point at localhost. |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | CORS allowlist. |
| `CODE_LENGTH` | `6` | Characters per short code. |
| `CODE_MAX_ATTEMPTS` | `5` | Collision retries before giving up. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend → backend. Set in `frontend/.env.local`. |

---

## Troubleshooting

**"Can't reach the API. Is the backend running on :8000?"**
The frontend is up but the backend isn't. Start it (step 1).

**"That API key isn't valid."**
The key doesn't match any hash in the database. Mint a fresh one (step 2). Note that
deleting `shortener.db` destroys all keys along with the links.

**CORS errors in the browser console**
The frontend is on an origin other than `http://localhost:3000`. Set `FRONTEND_ORIGIN` to
match and restart the backend.

**Clicks aren't counting**
Check the redirect is still a `307`, not a `301`. Browsers cache a 301 forever, so clicks
stop reaching the server. This is the one failure mode that looks like everything works.

**`ModuleNotFoundError` when running pytest**
Run it from `project-b-ai-assisted/` (not `backend/`). `pytest.ini` puts `backend/` on the
path.
