"""Regression: get_player_metric's create path (no metric yet this season) must
honour the seam's add() contract. This exact line kept the old Firestore tuple
unpacking after add() switched to returning the id - crashing the first reminder
for any user without a current-season metric."""
from tests.helpers import seed_user
from Enums.Role import Role
from Enums.UserState import UserState


def test_get_player_metric_creates_a_season_record_when_none_exists(data_access):
    user_to_state = seed_user(data_access, 5100, Role.PLAYER, UserState.DEFAULT)
    user = data_access.get_user_by_doc_id(user_to_state.user_id)

    metric = data_access.repository.get_player_metric(user)

    assert metric.doc_id is not None
    assert metric.user_id == user.doc_id
    # And the freshly created record is found (not re-created) on the next read.
    assert data_access.repository.get_player_metric(user).doc_id == metric.doc_id
