"""API key storage."""

import crud
import models


def test_raw_key_is_never_stored(db_session):
    """A leaked database must not hand over working credentials."""
    raw, row = crud.create_api_key(db_session, name="alice")

    stored = db_session.query(models.ApiKey).one()
    assert stored.key_hash != raw
    assert raw not in stored.key_hash

    # Nothing anywhere in the row echoes the plaintext back.
    assert raw not in repr(stored.__dict__)


def test_stored_value_is_a_sha256_hex_digest(db_session):
    raw, _ = crud.create_api_key(db_session, name="alice")
    stored = db_session.query(models.ApiKey).one()

    assert len(stored.key_hash) == 64
    assert crud.hash_key(raw) == stored.key_hash


def test_key_lookup_round_trips(db_session):
    raw, row = crud.create_api_key(db_session, name="alice")
    assert crud.get_api_key(db_session, raw).id == row.id


def test_unknown_key_resolves_to_nothing(db_session):
    crud.create_api_key(db_session, name="alice")
    assert crud.get_api_key(db_session, "not-a-real-key") is None


def test_two_keys_are_distinct(db_session):
    a, _ = crud.create_api_key(db_session, name="alice")
    b, _ = crud.create_api_key(db_session, name="bob")
    assert a != b
