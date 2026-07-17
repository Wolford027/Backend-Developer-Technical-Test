import re

import shortcode


def test_generates_code_of_configured_length():
    assert len(shortcode.generate(length=6)) == 6


def test_generates_only_base62_characters():
    code = shortcode.generate(length=6)
    assert re.fullmatch(r"[0-9A-Za-z]{6}", code)


def test_generates_different_codes_on_successive_calls():
    codes = {shortcode.generate(length=6) for _ in range(100)}
    # 62^6 keyspace; 100 draws colliding would mean the source isn't random.
    assert len(codes) == 100
