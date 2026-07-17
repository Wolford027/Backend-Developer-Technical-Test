# Backend Technical Challenge

Two small full-stack apps built the same way — FastAPI + SQLite backend, Next.js + React
frontend — to show two different working styles side by side.

| Project | What it is | How it was built |
|---|---|---|
| **[project-a-manual/](project-a-manual/)** | A Notes CRUD API | Written by hand |
| **[project-b-ai-assisted/](project-b-ai-assisted/)** | A URL shortener with API-key auth and click tracking | Built with Claude (transcript included) |

## Project A — Notes API

A small CRUD app for creating, reading, updating, and deleting text notes.

- **Stack:** FastAPI + SQLAlchemy backend, Next.js (App Router, TypeScript) frontend, SQLite.
- **Docs:** [project-a-manual/docs/notes-api.md](project-a-manual/docs/notes-api.md)

```bash
cd project-a-manual/backend
python3 -m venv venv && source venv/bin/activate
pip install fastapi uvicorn sqlalchemy
uvicorn main:app --reload
# frontend in a second terminal: cd ../frontend && npm install && npm run dev
```

## Project B — URL Shortener

Shorten long URLs, redirect visitors, count the clicks. API keys own their links, so the
dashboard and stats only ever show links created with the calling key.

- **Stack:** FastAPI + SQLAlchemy + Pydantic backend, Next.js + React + TypeScript frontend,
  SQLite, 44 tests (mutation-tested).
- **Docs:** [project-b-ai-assisted/README.md](project-b-ai-assisted/README.md) ·
  [design doc](project-b-ai-assisted/docs/2026-07-17-url-shortener-design.md) ·
  [API](project-b-ai-assisted/docs/API.md) ·
  [setup](project-b-ai-assisted/docs/SETUP.md) ·
  [AI transcript](project-b-ai-assisted/prompts/)

```bash
cd project-b-ai-assisted/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
python seed_key.py "my-laptop"     # prints an API key, once
# frontend in a second terminal: cd ../frontend && npm install && npm run dev
```

## Requirements

Python 3.10+ and Node 18+. Each project runs independently — see its own docs for full setup,
configuration, and troubleshooting.
