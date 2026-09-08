"""Unit: the SHV sync job end to end against the in-memory backend - configured
teams get imports/updates plus a trainer notification, unconfigured teams and
no-change runs stay silent."""
import pandas as pd
import pytest

from features.shvsync import ShvApiClient
from features.shvsync.ShvApiClient import ShvGame
from features.shvsync.ShvSyncService import ShvSyncService

from Utils import DateTimeUtils


class _RecordingTelegram:
    def __init__(self):
        self.trainer_messages = []

    async def send_info_message_to_trainers(self, message, event_type):
        self.trainer_messages.append(message)

    async def report_exception(self, description, error, *args):
        # Surface any swallowed failure instead of letting the test pass silently.
        raise AssertionError(f'{description}: {error!r}')


def _ts(day: int, hour: int = 18) -> pd.Timestamp:
    return DateTimeUtils.add_zurich_timezone(pd.Timestamp(2030, 11, day, hour, 30))


def _shv_game(shv_game_id=501, day=1, opponent='HC Arbon 3', location='Uzwil bzu'):
    return ShvGame(shv_game_id=shv_game_id, timestamp=_ts(day),
                   opponent=opponent, location=location, is_played=False)


@pytest.fixture
def sync(data_access, monkeypatch):
    """The service under test plus knobs: set the feed the fake API returns and
    read the recorded trainer messages."""
    telegram = _RecordingTelegram()
    service = ShvSyncService(data_access, telegram)
    feed = []

    async def fake_fetch_games(shv_team_id):
        return list(feed)

    monkeypatch.setattr(ShvApiClient, 'fetch_games', fake_fetch_games)
    return service, telegram, feed


async def test_team_without_shv_team_id_is_skipped(sync, data_access):
    service, telegram, feed = sync
    feed.append(_shv_game())

    await service.sync_all_teams(context=None)

    assert data_access.get_ordered_games() == []
    assert telegram.trainer_messages == []


async def test_new_game_is_imported_and_trainers_notified(sync, data_access):
    service, telegram, feed = sync
    data_access.set_shv_team_id(41317)
    feed.append(_shv_game())

    await service.sync_all_teams(context=None)

    games = data_access.get_ordered_games()
    assert len(games) == 1
    assert games[0].opponent == 'HC Arbon 3'
    assert games[0].shv_game_id == 501
    assert len(telegram.trainer_messages) == 1
    assert 'Hc Arbon 3' in telegram.trainer_messages[0]  # pretty_print_long .title()s names


async def test_moved_game_is_updated_in_place_and_change_reported(sync, data_access):
    service, telegram, feed = sync
    data_access.set_shv_team_id(41317)
    feed.append(_shv_game(day=1))
    await service.sync_all_teams(context=None)
    original_doc_id = data_access.get_ordered_games()[0].doc_id

    feed[0] = _shv_game(day=8, location='Wil Lindenhof')
    await service.sync_all_teams(context=None)

    games = data_access.get_ordered_games()
    assert len(games) == 1
    assert games[0].doc_id == original_doc_id
    assert games[0].timestamp == _ts(8)
    assert games[0].location == 'Wil Lindenhof'
    assert len(telegram.trainer_messages) == 2
    assert '01.11.2030' in telegram.trainer_messages[1]
    assert '08.11.2030' in telegram.trainer_messages[1]


async def test_unchanged_feed_sends_no_notification(sync, data_access):
    service, telegram, feed = sync
    data_access.set_shv_team_id(41317)
    feed.append(_shv_game())
    await service.sync_all_teams(context=None)

    await service.sync_all_teams(context=None)

    assert len(data_access.get_ordered_games()) == 1
    assert len(telegram.trainer_messages) == 1


async def test_played_games_are_ignored(sync, data_access):
    service, telegram, feed = sync
    data_access.set_shv_team_id(41317)
    feed.append(ShvGame(shv_game_id=502, timestamp=_ts(2), opponent='HC Rheintal 2',
                        location='Wil Lindenhof', is_played=True))

    await service.sync_all_teams(context=None)

    assert data_access.get_ordered_games() == []
    assert telegram.trainer_messages == []


async def test_vanished_game_is_reported_but_kept(sync, data_access):
    service, telegram, feed = sync
    data_access.set_shv_team_id(41317)
    feed.append(_shv_game())
    await service.sync_all_teams(context=None)

    feed.clear()
    await service.sync_all_teams(context=None)

    assert len(data_access.get_ordered_games()) == 1  # never deleted automatically
    assert len(telegram.trainer_messages) == 2
    assert 'no longer on the SHV schedule' in telegram.trainer_messages[1]
