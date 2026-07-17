"""Short code generation.

Pure and dependency-free so it can be tested without a database.
"""

import secrets
import string

ALPHABET = string.digits + string.ascii_letters  # base62


def generate(length: int) -> str:
    """Return a random base62 code.

    Drawn from `secrets`, not `random`: codes are the only thing standing
    between a private link and anyone who guesses it, so the generator must
    not be seedable or predictable from prior outputs.
    """
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
