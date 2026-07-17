import pytest
from pydantic import ValidationError

import schemas


def test_accepts_a_plain_https_url():
    assert schemas.LinkCreate(url="https://example.com/a").url == "https://example.com/a"


def test_accepts_http_as_well_as_https():
    assert schemas.LinkCreate(url="http://example.com").url == "http://example.com"


@pytest.mark.parametrize(
    "hostile_url",
    [
        "javascript:alert(document.cookie)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
    ],
)
def test_rejects_non_http_schemes(hostile_url):
    """These are syntactically valid URLs but unsafe redirect destinations.

    We hand long_url straight to a browser, so a javascript: or data: target
    makes every click execute attacker script -- stored XSS, not untidiness.
    """
    with pytest.raises(ValidationError):
        schemas.LinkCreate(url=hostile_url)


def test_rejects_garbage_that_is_not_a_url_at_all():
    with pytest.raises(ValidationError):
        schemas.LinkCreate(url="not a url")


def test_rejects_urls_longer_than_2048_chars():
    with pytest.raises(ValidationError):
        schemas.LinkCreate(url="https://example.com/" + "a" * 2048)


def test_rejects_a_negative_ttl():
    with pytest.raises(ValidationError):
        schemas.LinkCreate(url="https://example.com", expires_in_days=-1)


def test_ttl_is_optional_and_defaults_to_never_expiring():
    assert schemas.LinkCreate(url="https://example.com").expires_in_days is None
