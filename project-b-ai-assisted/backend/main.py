from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

import config
import crud
import models
import schemas
from auth import require_api_key
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener API",
    description="Shorten URLs, redirect visitors, and count clicks.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _to_out(link: models.Link) -> dict:
    return {
        "code": link.code,
        "short_url": f"{config.BASE_URL}/{link.code}",
        "long_url": link.long_url,
        "click_count": link.click_count,
        "created_at": link.created_at,
        "expires_at": link.expires_at,
    }


# --- Management API (authenticated) -----------------------------------------
# Declared before /{code}: FastAPI matches routes in order, and a bare
# /{code} would otherwise swallow /api/links as a code named "api".


@app.post("/api/links", response_model=schemas.LinkOut, status_code=201)
def create_link(
    payload: schemas.LinkCreate,
    response: Response,
    db: Session = Depends(get_db),
    api_key: models.ApiKey = Depends(require_api_key),
):
    """Shorten a URL.

    Returns 201 for a new link, or 200 with the existing code if this key has
    already shortened this URL -- nothing was created, so 201 would be a lie.
    """
    existing = crud.find_duplicate(db, payload.url, api_key.id)
    if existing is not None:
        response.status_code = 200
        return _to_out(existing)

    link = crud.create_link(db, payload.url, api_key.id, payload.expires_in_days)
    return _to_out(link)


@app.get("/api/links", response_model=list[schemas.LinkOut])
def list_links(
    db: Session = Depends(get_db),
    api_key: models.ApiKey = Depends(require_api_key),
):
    """List links owned by the calling key."""
    return [_to_out(link) for link in crud.get_links_for_key(db, api_key.id)]


@app.get("/api/links/{code}/stats", response_model=schemas.StatsOut)
def link_stats(
    code: str,
    db: Session = Depends(get_db),
    api_key: models.ApiKey = Depends(require_api_key),
):
    """Click count for one link.

    404 when the calling key doesn't own the code -- deliberately the same
    response as a code that doesn't exist, so stats can't be used to probe
    whether another key's link exists.
    """
    link = crud.get_link_for_key(db, code, api_key.id)
    if link is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    out = _to_out(link)
    out["is_expired"] = link.is_expired()
    return out


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Public redirect ---------------------------------------------------------


@app.get("/{code}", include_in_schema=False)
def redirect(code: str, db: Session = Depends(get_db)):
    """Resolve a short code and redirect. Public -- no API key.

    307, not 301: a 301 is cached by the browser indefinitely, so every click
    after the first would never reach us and the click counter would silently
    stop moving. Cache-Control reinforces it for intermediary caches.
    """
    link = crud.get_link_by_code(db, code)
    if link is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    if link.is_expired():
        # 410, not 404: "this link died" and "this link never existed" are
        # different facts, and which one it is decides what the user does next.
        raise HTTPException(status_code=410, detail="This short link has expired")

    crud.increment_click_count(db, link.id)

    return RedirectResponse(
        url=link.long_url,
        status_code=307,
        headers={"Cache-Control": "no-store, max-age=0"},
    )
