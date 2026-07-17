from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

import config

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Request-scoped session.

    Lives here rather than in main.py so tests can override it by importing
    from the same place the routes do.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
