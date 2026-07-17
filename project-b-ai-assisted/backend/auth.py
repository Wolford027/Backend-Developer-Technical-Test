"""API key authentication."""

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

import crud
import models
from database import get_db

# auto_error=False so a missing key reaches our handler and gets the same
# response as an invalid one (see below).
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=401,
    detail="Invalid or missing API key",
    headers={"WWW-Authenticate": "X-API-Key"},
)


def require_api_key(
    raw_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> models.ApiKey:
    """Resolve the caller's key, or 401.

    Missing and invalid keys return an identical response on purpose. A
    distinct "that key doesn't exist" message would confirm which keys are
    real, handing an attacker an oracle to enumerate valid keys against.
    """
    if not raw_key:
        raise _UNAUTHORIZED

    api_key = crud.get_api_key(db, raw_key)
    if api_key is None:
        raise _UNAUTHORIZED

    return api_key
