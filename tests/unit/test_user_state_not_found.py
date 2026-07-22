"""Unit: the two not-found paths in the repository must raise ObjectNotFoundException.

Both were previously broken and untested:
- get_user_state indexed res[0] on an empty result -> IndexError, masking the intended
  ObjectNotFoundException that callers (e.g. NodeHandler's INIT fallback) catch.
- update_user_state_via_user_id returned the exception object instead of raising it, so
  a missing state doc made the user-state update silently no-op.
"""
import pytest

from Enums.UserState import UserState
from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState
from Utils.CustomExceptions import ObjectNotFoundException


def test_get_user_state_raises_object_not_found_when_no_state_doc(data_access):
    user = TelegramUser(123, "Ghost", "User", doc_id="user-doc-without-state")

    with pytest.raises(ObjectNotFoundException):
        data_access.repository.get_user_state(user)


def test_update_user_state_via_user_id_raises_when_state_doc_missing(data_access):
    # doc_id is None -> DataAccess.update routes to update_user_state_via_user_id,
    # whose lookup finds no matching state doc.
    users_to_state = UsersToState("ghost-user-id", UserState.DEFAULT)

    with pytest.raises(ObjectNotFoundException):
        data_access.update(users_to_state)
