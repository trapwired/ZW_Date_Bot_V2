"""Unit: mapping the SHV matchcenter payload onto ShvGame (the HTTP call itself is
not under test - parse_game is the seam)."""
from features.shvsync.ShvApiClient import parse_game

TEAM_ID = 41317


def _payload(**overrides):
    payload = {
        'objectId': 509764,
        'gameDateTime': '2026-11-21T18:30:00',
        'homeTeamId': TEAM_ID,
        'homeTeamName': 'SG KTV Wil / HC Uzwil 2',
        'awayTeamName': 'HC Arbon 3',
        'venueName': 'Uzwil bzu',
        'gameStatusId': 1,
    }
    payload.update(overrides)
    return payload


def test_home_game_takes_the_away_team_as_opponent():
    game = parse_game(_payload(), TEAM_ID)

    assert game.shv_game_id == 509764
    assert game.opponent == 'HC Arbon 3'
    assert game.location == 'Uzwil bzu'
    assert not game.is_played


def test_away_game_takes_the_home_team_as_opponent():
    game = parse_game(_payload(homeTeamId=40901, homeTeamName='BSV Bischofszell 1'), TEAM_ID)

    assert game.opponent == 'BSV Bischofszell 1'


def test_game_datetime_is_interpreted_as_zurich_wall_clock():
    game = parse_game(_payload(), TEAM_ID)

    assert str(game.timestamp.tz) == 'Europe/Zurich'
    assert game.timestamp.strftime('%d.%m.%Y %H:%M') == '21.11.2026 18:30'


def test_played_game_is_flagged():
    game = parse_game(_payload(gameStatusId=2), TEAM_ID)

    assert game.is_played
