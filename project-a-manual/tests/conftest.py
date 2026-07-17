import os
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# The backend uses bare imports (`import models`, `from database import ...`),
# so its directory has to be importable directly.
BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
sys.path.insert(0, BACKEND_DIR)


@pytest.fixture
def client():
    """A TestClient backed by a throwaway SQLite file.

    database.py hardcodes sqlite:///./notes.db and main.py calls
    create_all() at import time, so we repoint the database module at a
    temp file *before* importing the app to keep the suite hermetic.
    """
    import database

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    engine = create_engine(
        f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    database.engine = engine
    database.SessionLocal = TestingSessionLocal

    import main

    main.Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db

    with TestClient(main.app) as c:
        yield c

    main.app.dependency_overrides.clear()
    engine.dispose()
    os.unlink(tmp.name)
