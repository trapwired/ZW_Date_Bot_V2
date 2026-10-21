"""The calendar link's secret: minted once, stored only as its sha256 hash, and
parsed back out of the requested feed file name (`<token>.ics`)."""
import hashlib
import re
import secrets

TOKEN_BYTES = 30  # 240 bit -> 40 url-safe characters; too many to guess, no lockout needed

FEED_FILE_PATTERN = re.compile(r'^([A-Za-z0-9_-]{40})\.ics$')


def mint_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def token_from_feed_file_name(name: str) -> str | None:
    # fullmatch, not match: '$' would also accept a trailing newline.
    match = FEED_FILE_PATTERN.fullmatch(name)
    return match.group(1) if match else None
