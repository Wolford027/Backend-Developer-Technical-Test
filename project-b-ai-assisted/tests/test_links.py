"""Creating links, redirecting, counting clicks, and the named edge cases."""

from datetime import timedelta

import pytest

import crud
import models
import shortcode


# --- create ------------------------------------------------------------------


def test_create_returns_201_and_a_usable_short_url(client, auth):
    r = client.post("/api/links", json={"url": "https://example.com/a"}, headers=auth)

    assert r.status_code == 201
    body = r.json()
    assert len(body["code"]) == 6
    assert body["long_url"] == "https://example.com/a"
    assert body["short_url"].endswith("/" + body["code"])
    assert body["click_count"] == 0
    assert body["expires_at"] is None


def test_create_rejects_a_javascript_url(client, auth):
    r = client.post(
        "/api/links", json={"url": "javascript:alert(1)"}, headers=auth
    )
    assert r.status_code == 422


def test_create_rejects_garbage(client, auth):
    r = client.post("/api/links", json={"url": "not a url"}, headers=auth)
    assert r.status_code == 422


def test_two_different_urls_get_different_codes(client, auth):
    a = client.post("/api/links", json={"url": "https://a.com"}, headers=auth).json()
    b = client.post("/api/links", json={"url": "https://b.com"}, headers=auth).json()
    assert a["code"] != b["code"]


# --- duplicates --------------------------------------------------------------


def test_same_url_twice_returns_the_same_code_with_200(client, auth):
    first = client.post("/api/links", json={"url": "https://dup.com"}, headers=auth)
    second = client.post("/api/links", json={"url": "https://dup.com"}, headers=auth)

    assert first.status_code == 201
    assert second.status_code == 200  # nothing was created
    assert first.json()["code"] == second.json()["code"]


def test_duplicate_does_not_create_a_second_row(client, auth, db_session):
    client.post("/api/links", json={"url": "https://dup.com"}, headers=auth)
    client.post("/api/links", json={"url": "https://dup.com"}, headers=auth)

    assert db_session.query(models.Link).count() == 1


def test_dedup_is_scoped_per_key_not_global(client, auth, other_auth):
    """Two keys shortening the same URL must get different codes.

    Sharing a code would pool their click counts and leak one key's activity
    into the other's dashboard.
    """
    mine = client.post("/api/links", json={"url": "https://same.com"}, headers=auth)
    theirs = client.post(
        "/api/links", json={"url": "https://same.com"}, headers=other_auth
    )

    assert mine.status_code == 201
    assert theirs.status_code == 201
    assert mine.json()["code"] != theirs.json()["code"]


def test_duplicate_of_an_expired_link_mints_a_fresh_code(client, auth, db_session):
    """Handing back a dead code to someone asking for a fresh one is a bug."""
    first = client.post(
        "/api/links",
        json={"url": "https://expiring.com", "expires_in_days": 1},
        headers=auth,
    ).json()

    link = crud.get_link_by_code(db_session, first["code"])
    link.expires_at = models.utcnow() - timedelta(days=1)
    db_session.commit()

    second = client.post(
        "/api/links", json={"url": "https://expiring.com"}, headers=auth
    )

    assert second.status_code == 201
    assert second.json()["code"] != first["code"]


# --- redirect ----------------------------------------------------------------


def test_redirect_sends_307_to_the_original_url(client, auth):
    code = client.post(
        "/api/links", json={"url": "https://example.com/dest"}, headers=auth
    ).json()["code"]

    r = client.get(f"/{code}", follow_redirects=False)

    assert r.status_code == 307
    assert r.headers["location"] == "https://example.com/dest"


def test_redirect_is_not_cacheable(client, auth):
    """A cached redirect never reaches the server, so clicks stop counting."""
    code = client.post(
        "/api/links", json={"url": "https://example.com/x"}, headers=auth
    ).json()["code"]

    r = client.get(f"/{code}", follow_redirects=False)

    assert "no-store" in r.headers["cache-control"]


def test_unknown_code_is_404(client):
    assert client.get("/nope12", follow_redirects=False).status_code == 404


def test_expired_code_is_410_not_404(client, auth, db_session):
    """410 Gone and 404 Not Found are different facts.

    "It expired" tells the user to ask for a new link; "never existed" tells
    them to check their typo. Collapsing both into 404 destroys that signal.
    """
    code = client.post(
        "/api/links",
        json={"url": "https://example.com/old", "expires_in_days": 1},
        headers=auth,
    ).json()["code"]

    link = crud.get_link_by_code(db_session, code)
    link.expires_at = models.utcnow() - timedelta(seconds=1)
    db_session.commit()

    r = client.get(f"/{code}", follow_redirects=False)

    assert r.status_code == 410


def test_unexpired_link_still_redirects(client, auth):
    code = client.post(
        "/api/links",
        json={"url": "https://example.com/live", "expires_in_days": 30},
        headers=auth,
    ).json()["code"]

    assert client.get(f"/{code}", follow_redirects=False).status_code == 307


# --- click counting ----------------------------------------------------------


def test_clicks_are_counted(client, auth):
    code = client.post(
        "/api/links", json={"url": "https://example.com/c"}, headers=auth
    ).json()["code"]

    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False)

    stats = client.get(f"/api/links/{code}/stats", headers=auth).json()
    assert stats["click_count"] == 3


def test_a_failed_redirect_counts_nothing(client, auth, db_session):
    """404s and 410s must not inflate anyone's numbers."""
    code = client.post(
        "/api/links",
        json={"url": "https://example.com/e", "expires_in_days": 1},
        headers=auth,
    ).json()["code"]

    link = crud.get_link_by_code(db_session, code)
    link.expires_at = models.utcnow() - timedelta(seconds=1)
    db_session.commit()

    client.get(f"/{code}", follow_redirects=False)  # 410
    client.get("/nope12", follow_redirects=False)  # 404

    db_session.refresh(link)
    assert link.click_count == 0


# --- stats -------------------------------------------------------------------


def test_stats_reports_zero_for_a_fresh_link(client, auth):
    code = client.post(
        "/api/links", json={"url": "https://example.com/s"}, headers=auth
    ).json()["code"]

    stats = client.get(f"/api/links/{code}/stats", headers=auth).json()

    assert stats["click_count"] == 0
    assert stats["is_expired"] is False


def test_stats_for_unknown_code_is_404(client, auth):
    assert client.get("/api/links/nope12/stats", headers=auth).status_code == 404


# --- ownership ---------------------------------------------------------------


def test_dashboard_only_lists_links_owned_by_the_calling_key(client, auth, other_auth):
    client.post("/api/links", json={"url": "https://mine.com"}, headers=auth)
    client.post("/api/links", json={"url": "https://theirs.com"}, headers=other_auth)

    mine = client.get("/api/links", headers=auth).json()

    assert [link["long_url"] for link in mine] == ["https://mine.com"]


def test_one_key_cannot_read_another_keys_stats(client, auth, other_auth):
    """The authorization boundary -- this is the one that fails silently."""
    code = client.post(
        "/api/links", json={"url": "https://private.com"}, headers=auth
    ).json()["code"]

    r = client.get(f"/api/links/{code}/stats", headers=other_auth)

    assert r.status_code == 404


# --- code collisions ---------------------------------------------------------


def test_collision_retries_and_still_mints_a_unique_code(
    client, auth, db_session, monkeypatch
):
    """Force the retry branch that 57 billion codes make unreachable by chance.

    The generator returns a taken code once, then a free one. Without the
    retry this raises IntegrityError; with it, the caller never notices.
    """
    taken = client.post(
        "/api/links", json={"url": "https://first.com"}, headers=auth
    ).json()["code"]

    codes = iter([taken, "fresh1"])
    monkeypatch.setattr(shortcode, "generate", lambda length: next(codes))

    r = client.post("/api/links", json={"url": "https://second.com"}, headers=auth)

    assert r.status_code == 201
    assert r.json()["code"] == "fresh1"


def test_gives_up_after_max_attempts(client, auth, monkeypatch):
    """Exhausting retries must raise, not loop forever or return a bad link."""
    taken = client.post(
        "/api/links", json={"url": "https://first.com"}, headers=auth
    ).json()["code"]

    monkeypatch.setattr(shortcode, "generate", lambda length: taken)

    with pytest.raises(RuntimeError, match="unique code"):
        client.post("/api/links", json={"url": "https://second.com"}, headers=auth)
