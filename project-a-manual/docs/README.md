# Notes API

A small CRUD app for creating and managing text notes. Built this as a starting point for learning the FastAPI + Next.js combo — nothing fancy, just create/read/update/delete notes with a SQLite database under the hood.

**Stack:** FastAPI + SQLAlchemy on the backend, Next.js (App Router, TypeScript) on the frontend.

## Getting it running

You'll need Python 3.10+ and Node 18+ installed. Two terminals, one for each half of the app.

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install fastapi uvicorn sqlalchemy
uvicorn main:app --reload
```

That spins up the API at `localhost:8000`. First time you run it, SQLAlchemy will create a `notes.db` file in the folder automatically — no migrations to run manually.

### Frontend

```bash
cd frontend
npm install
```

Add a `.env.local` in the frontend folder:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then:

```bash
npm run dev
```

App's at `localhost:3000`. Backend needs to already be running for it to actually load any notes.

## Project layout

```
backend/
  database.py    -> DB connection/session
  models.py      -> SQLAlchemy table def
  schemas.py     -> Pydantic request/response shapes
  crud.py        -> actual DB queries
  main.py        -> routes live here

frontend/
  app/page.tsx   -> the notes UI
  lib/api.ts     -> fetch calls to the backend
  types/note.ts  -> shared TS types
```

## API docs

Didn't write these by hand — FastAPI generates them from the code itself, so they stay in sync automatically.

- `localhost:8000/docs` — Swagger, lets you actually test endpoints from the browser
- `localhost:8000/redoc` — cleaner read-only version if you just want to look something up
- `localhost:8000/openapi.json` — raw schema, useful if you want to import into Postman

Endpoints, for reference:

```
GET    /notes         list all notes
GET    /notes/{id}    get one note
POST   /notes         create a note        { title, content? }
PUT    /notes/{id}    update a note        { title?, content? }
DELETE /notes/{id}    delete a note
```

## Things that'll probably trip you up

**CORS errors in the console** — the backend only allows `localhost:3000` by default (set in the `CORSMiddleware` block in `main.py`). If your frontend's running on a different port, update that list.

**Port 8000 already taken** — run `uvicorn main:app --reload --port 8001` instead, just remember to update `NEXT_PUBLIC_API_URL` to match.

**Weird/stale data while messing with the schema** — easiest fix is just deleting `notes.db` and restarting the server. It'll rebuild fresh.

**`ModuleNotFoundError` on the backend** — almost always means the venv isn't activated. Reactivate it and reinstall if needed.

## Notes to self / possible next steps

- Add pagination once there's actually enough notes to matter
- Move the DB URL out of `database.py` and into an env var
- Auth, if this ever needs to be more than a single-user toy project