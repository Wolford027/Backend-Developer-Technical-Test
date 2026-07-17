"""Mint an API key.

    python seed_key.py "my-laptop"

The raw key is printed once and never stored -- only its SHA-256 lands in the
database. If it's lost, mint another; there is no recovery path, by design.
"""

import sys

import crud
from database import Base, SessionLocal, engine


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "default"

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        raw_key, row = crud.create_api_key(db, name=name)
    finally:
        db.close()

    print(f"\n  API key for {row.name!r} created.\n")
    print(f"    {raw_key}\n")
    print("  Save it now -- it is not recoverable.")
    print("  Use it as the X-API-Key header, or paste it into the frontend.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
