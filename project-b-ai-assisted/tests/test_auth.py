"""The authentication boundary: creating links needs a key, redirects do not."""

PROTECTED = [
    ("post", "/api/links"),
    ("get", "/api/links"),
    ("get", "/api/links/abc123/stats"),
]


def test_create_without_a_key_is_rejected(client):
    r = client.post("/api/links", json={"url": "https://example.com"})
    assert r.status_code == 401


def test_create_with_an_unknown_key_is_rejected(client):
    r = client.post(
        "/api/links",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "totally-made-up"},
    )
    assert r.status_code == 401


def test_every_management_endpoint_requires_a_key(client):
    for method, path in PROTECTED:
        kwargs = {"json": {"url": "https://example.com"}} if method == "post" else {}
        r = getattr(client, method)(path, **kwargs)
        assert r.status_code == 401, f"{method.upper()} {path} was not protected"


def test_missing_and_invalid_keys_are_indistinguishable(client):
    """Both say the same thing.

    If a wrong key produced a different message than a missing one, the API
    would confirm which keys exist -- an oracle for guessing valid keys.
    """
    missing = client.get("/api/links")
    invalid = client.get("/api/links", headers={"X-API-Key": "nope"})
    assert missing.status_code == invalid.status_code == 401
    assert missing.json()["detail"] == invalid.json()["detail"]


def test_valid_key_is_accepted(client, auth):
    r = client.get("/api/links", headers=auth)
    assert r.status_code == 200


def test_redirects_are_public(client, auth):
    code = client.post(
        "/api/links", json={"url": "https://example.com/x"}, headers=auth
    ).json()["code"]

    r = client.get(f"/{code}", follow_redirects=False)  # no auth header

    assert r.status_code == 307
