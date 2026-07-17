def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_notes_starts_empty(client):
    resp = client.get("/notes")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_note(client):
    resp = client.post("/notes", json={"title": "First", "content": "Hello"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] > 0
    assert body["title"] == "First"
    assert body["content"] == "Hello"
    assert body["created_at"] is not None


def test_create_note_content_optional(client):
    resp = client.post("/notes", json={"title": "Just a title"})
    assert resp.status_code == 201
    assert resp.json()["content"] is None


def test_get_note(client):
    created = client.post("/notes", json={"title": "Read me"}).json()
    resp = client.get(f"/notes/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Read me"


def test_get_missing_note_returns_404(client):
    resp = client.get("/notes/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Note not found"


def test_update_note(client):
    created = client.post("/notes", json={"title": "Old", "content": "old body"}).json()
    resp = client.put(
        f"/notes/{created['id']}", json={"title": "New", "content": "new body"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New"
    assert body["content"] == "new body"


def test_partial_update_keeps_other_fields(client):
    created = client.post("/notes", json={"title": "Keep", "content": "body"}).json()
    resp = client.put(f"/notes/{created['id']}", json={"content": "changed"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Keep"
    assert body["content"] == "changed"


def test_update_missing_note_returns_404(client):
    resp = client.put("/notes/999", json={"title": "Nope"})
    assert resp.status_code == 404


def test_delete_note(client):
    created = client.post("/notes", json={"title": "Delete me"}).json()
    resp = client.delete(f"/notes/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/notes/{created['id']}").status_code == 404


def test_delete_missing_note_returns_404(client):
    resp = client.delete("/notes/999")
    assert resp.status_code == 404


def test_list_returns_all_created_notes(client):
    # Note: crud orders by created_at desc, but SQLite's func.now() only has
    # 1-second resolution, so rapid inserts share a timestamp and their
    # relative order is not deterministic — assert membership, not order.
    client.post("/notes", json={"title": "one"})
    client.post("/notes", json={"title": "two"})
    titles = {n["title"] for n in client.get("/notes").json()}
    assert titles == {"one", "two"}
