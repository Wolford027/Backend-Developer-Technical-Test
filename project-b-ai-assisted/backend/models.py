from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    # SHA-256 of the raw key. The plaintext is shown once at creation and is
    # unrecoverable afterwards, so a leaked database yields no working keys.
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    links = relationship("Link", back_populates="api_key")


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    # UNIQUE is what makes the generator's collision retry correct: the
    # database, not the application, is the arbiter of uniqueness.
    code = Column(String, unique=True, nullable=False, index=True)
    long_url = Column(String, nullable=False)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False, index=True)
    click_count = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    expires_at = Column(DateTime, nullable=True)  # NULL = never expires

    api_key = relationship("ApiKey", back_populates="links")

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        now = now or utcnow()
        expires_at = self.expires_at
        # SQLite hands back naive datetimes; compare like with like.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return now >= expires_at


# Dedup is scoped per key, and this index is the lookup that does it.
Index("ix_links_owner_url", Link.api_key_id, Link.long_url)
