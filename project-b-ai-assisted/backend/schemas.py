"""Request and response models.

The URL validator here is a security boundary, not a formatting nicety --
see `validate_url`.
"""


from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator
from pydantic import HttpUrl

import config

# HttpUrl enforces BOTH syntax and an http/https scheme allowlist: it rejects
# javascript:, data:, file: and ftp: on its own. Verified by mutation testing,
# which is the only reason we know -- an earlier version of this file also had
# an explicit `if scheme not in ("http","https")` guard, and deleting that
# guard broke no test, because it was unreachable. Dead code that appears to
# enforce a security property is worse than none: it draws the eye away from
# the thing actually doing the work.
#
# The safety of the redirect therefore rests on this one line. If it is ever
# swapped for AnyUrl or a plain str, the scheme allowlist silently disappears
# with it -- test_schemas.py::test_rejects_non_http_schemes is what stops that
# from shipping.
_http_url = TypeAdapter(HttpUrl)


class LinkCreate(BaseModel):
    url: str
    expires_in_days: Optional[Annotated[int, Field(ge=1, le=3650)]] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Reject anything we would not be willing to redirect a browser to.

        `javascript:alert(1)` and `data:text/html,...` are syntactically valid
        URLs. The redirect hands long_url straight to the browser, so accepting
        one would turn every click on that short link into stored XSS. HttpUrl
        rejects them -- see the note on _http_url for why that is load-bearing.

        Length is checked before parsing: no point handing a megabyte of text
        to the URL parser to find out it is too long.
        """
        v = v.strip()
        if len(v) > config.MAX_URL_LENGTH:
            raise ValueError(f"URL exceeds {config.MAX_URL_LENGTH} characters")

        _http_url.validate_python(v)  # scheme allowlist + syntax; raises on both
        return v


class LinkOut(BaseModel):
    code: str
    short_url: str
    long_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StatsOut(BaseModel):
    code: str
    short_url: str
    long_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_expired: bool

    model_config = ConfigDict(from_attributes=True)
