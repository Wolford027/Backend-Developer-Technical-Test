"""Data access.

Deliberately imports no FastAPI: this layer is testable without HTTP, and
HTTP concerns (status codes, headers) stay in main.py where they belong.
"""

import hashlib
import secrets
from datetime import timedelta
from typing import Optional

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import config
import models
import shortcode


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_api_key(db: Session, name: str) -> tuple[str, models.ApiKey]:
    """Mint a key. Returns (raw_key, row) -- the raw key is never stored."""
    raw_key = secrets.token_urlsafe(32)
    row = models.ApiKey(key_hash=hash_key(raw_key), name=name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return raw_key, row


def get_api_key(db: Session, raw_key: str) -> Optional[models.ApiKey]:
    return (
        db.query(models.ApiKey)
        .filter(models.ApiKey.key_hash == hash_key(raw_key))
        .first()
    )


def get_link_by_code(db: Session, code: str) -> Optional[models.Link]:
    return db.query(models.Link).filter(models.Link.code == code).first()


def get_links_for_key(db: Session, api_key_id: int) -> list[models.Link]:
    return (
        db.query(models.Link)
        .filter(models.Link.api_key_id == api_key_id)
        .order_by(models.Link.created_at.desc())
        .all()
    )


def get_link_for_key(db: Session, code: str, api_key_id: int) -> Optional[models.Link]:
    """Fetch a link only if this key owns it -- the authorization boundary."""
    return (
        db.query(models.Link)
        .filter(models.Link.code == code, models.Link.api_key_id == api_key_id)
        .first()
    )


def find_duplicate(db: Session, long_url: str, api_key_id: int) -> Optional[models.Link]:
    """An existing, live link to the same URL owned by the same key.

    Scoped per key, not global: if two keys shared a code, one tenant's clicks
    would land in the other's stats. Expired links are not reused -- returning
    a dead code to someone asking for a fresh one is just a broken link.
    """
    candidates = (
        db.query(models.Link)
        .filter(
            models.Link.long_url == long_url,
            models.Link.api_key_id == api_key_id,
        )
        .order_by(models.Link.created_at.desc())
        .all()
    )
    return next((c for c in candidates if not c.is_expired()), None)


def create_link(
    db: Session,
    long_url: str,
    api_key_id: int,
    expires_in_days: Optional[int] = None,
) -> models.Link:
    """Insert a link with a fresh code, retrying if the code collides.

    The retry leans on the UNIQUE constraint rather than a pre-check SELECT:
    "does this code exist?" followed by "insert it" is a TOCTOU race that two
    concurrent requests can both win.
    """
    expires_at = (
        models.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
    )

    for _ in range(config.CODE_MAX_ATTEMPTS):
        link = models.Link(
            code=shortcode.generate(config.CODE_LENGTH),
            long_url=long_url,
            api_key_id=api_key_id,
            expires_at=expires_at,
        )
        db.add(link)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(link)
        return link

    raise RuntimeError(
        f"could not generate a unique code in {config.CODE_MAX_ATTEMPTS} attempts"
    )


def increment_click_count(db: Session, link_id: int) -> None:
    """Count a click atomically, in SQL.

    Not `link.click_count += 1` in Python: two concurrent clicks would both
    read N and both write N+1, silently losing one. The database resolves it.
    """
    db.execute(
        update(models.Link)
        .where(models.Link.id == link_id)
        .values(click_count=models.Link.click_count + 1)
    )
    db.commit()
