"""Settings, read from the environment with sane local defaults."""

import os

# Where SQLite lives. Overridden in tests so they never touch the dev database.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shortener.db")

# Length of generated short codes. 62^6 ~= 57 billion.
CODE_LENGTH = int(os.getenv("CODE_LENGTH", "6"))

# How many times to retry when a generated code collides with an existing one.
CODE_MAX_ATTEMPTS = int(os.getenv("CODE_MAX_ATTEMPTS", "5"))

# Public origin of this API, used to build the full short URL in responses.
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

# Origin allowed to call the API from a browser.
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

MAX_URL_LENGTH = 2048
