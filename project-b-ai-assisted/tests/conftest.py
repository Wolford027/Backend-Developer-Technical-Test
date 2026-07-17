"""Shared test fixtures.

Every test runs against a throwaway SQLite file in a tmp_path, wired in via
FastAPI's dependency_overrides. Tests must never touch the dev database -- a
suite that wipes real data gets run once and then never trusted again.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import crud
import main
from database import Base, get_db


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()


@pytest.fixture
def api_key(db_session):
    """A raw API key owned by 'alice'."""
    raw, _ = crud.create_api_key(db_session, name="alice")
    return raw


@pytest.fixture
def other_api_key(db_session):
    """A second key owned by 'bob', for testing the ownership boundary."""
    raw, _ = crud.create_api_key(db_session, name="bob")
    return raw


@pytest.fixture
def auth(api_key):
    return {"X-API-Key": api_key}


@pytest.fixture
def other_auth(other_api_key):
    return {"X-API-Key": other_api_key}
