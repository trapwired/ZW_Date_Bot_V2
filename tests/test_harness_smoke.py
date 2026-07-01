"""Smoke tests: prove the harness wires up and the doubles behave.

If these pass, the in-memory Firestore + FakeBot stack is sound and NodeHandler's
startup invariants (do_checks) hold — the foundation for the characterization suite.
"""
from Enums.UserState import UserState
from domain.entities.TelegramUser import TelegramUser


def test_node_handler_builds_and_passes_do_checks(node_handler):
    # NodeHandler.__init__ now calls do_checks(); reaching here means every UserState
    # has a node and every described command has a description.
    assert node_handler is not None
    assert node_handler.get_node(UserState.DEFAULT) is not None


def test_data_access_user_roundtrip(data_access):
    user_to_state = data_access.add(TelegramUser(telegram_id=999, firstname="Ada", lastname="Lovelace"))
    assert user_to_state.state == UserState.INIT

    fetched = data_access.get_user(999)
    assert fetched.firstname == "Ada"
    assert fetched.telegramId == 999


def test_in_memory_firestore_is_isolated_per_test(data_access):
    # Should start empty every test; relies on a fresh FakeFirestoreClient per test.
    from Utils.CustomExceptions import ObjectNotFoundException
    import pytest
    with pytest.raises(ObjectNotFoundException):
        data_access.get_user(999)
