"""The calendar link's token: minting, hashing and parsing it out of `<token>.ics`."""
import re

import pytest

from domain.calendar.Tokens import hash_token, mint_token, token_from_feed_file_name

TOKEN_CHARSET = re.compile(r'[A-Za-z0-9_-]+')
VALID_TOKEN = 'A' * 20 + 'z9_-' * 5


def test_minted_token_is_40_url_safe_characters():
    token = mint_token()
    assert len(token) == 40
    assert TOKEN_CHARSET.fullmatch(token)


def test_minted_tokens_differ():
    assert len({mint_token() for _ in range(50)}) == 50


def test_minted_token_parses_back_out_of_its_feed_file_name():
    token = mint_token()
    assert token_from_feed_file_name(f'{token}.ics') == token


def test_hash_is_sha256_hex_and_deterministic():
    assert hash_token('abc') == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
    token = mint_token()
    assert hash_token(token) == hash_token(token)
    assert re.fullmatch(r'[a-f0-9]{64}', hash_token(token))


def test_different_tokens_hash_differently():
    assert hash_token(mint_token()) != hash_token(mint_token())


def test_well_formed_but_never_issued_name_still_parses():
    # Whether a token is known is decided by the hash lookup, not by its shape.
    assert token_from_feed_file_name(f'{VALID_TOKEN}.ics') == VALID_TOKEN


@pytest.mark.parametrize('name', [
    'x.ics',                        # unknown garbage
    '',
    f'{VALID_TOKEN[:39]}.ics',      # too short
    VALID_TOKEN,                    # no .ics
    f'{VALID_TOKEN}a.ics',          # one char too many
    f'{VALID_TOKEN}.ics.ics',
    f'{VALID_TOKEN}.ICS',
    f'{VALID_TOKEN}.ics\n',         # '$' alone would accept a trailing newline
    f'{VALID_TOKEN[:39]}+.ics',     # base64 '+', not url-safe
    f'{VALID_TOKEN[:39]}=.ics',     # padding
    f'../{VALID_TOKEN}.ics',
])
def test_malformed_feed_file_names_yield_no_token(name):
    assert token_from_feed_file_name(name) is None
