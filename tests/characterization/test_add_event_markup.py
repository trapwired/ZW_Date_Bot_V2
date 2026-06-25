"""Regression test for the inline-markup event-type bug.

Before Phase 1, AddEventFieldsNode.update_inline_message hardcoded
ADMIN_ADD_GAME / Event.GAME, so training & timekeeping add-flows produced inline
buttons whose callback_data carried the wrong event type. This pins the fix:
each event type's inline buttons must encode its OWN type.
"""
import pytest

from Enums.Role import Role
from Enums.UserState import UserState
from tests.helpers import drive, seed_user

ADMIN_ID = 600
FUTURE_TIMESTAMP = "24.12.2030 18:30"

CASES = [
    ("/game", "ADMIN_ADD_GAME#GAME#"),
    ("/training", "ADMIN_ADD_TRAINING#TRAINING#"),
    ("/timekeeping", "ADMIN_ADD_TIMEKEEPING#TIMEKEEPING#"),
]


def _all_callback_data(reply_markup):
    return [button.callback_data for row in reply_markup.inline_keyboard for button in row]


@pytest.mark.parametrize("add_command, expected_prefix", CASES)
async def test_inline_markup_encodes_correct_event_type(node_handler, data_access, bot,
                                                        add_command, expected_prefix):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_ADD)

    await drive(node_handler, ADMIN_ID, add_command)
    # The timestamp step triggers update_inline_message -> an inline-keyboard edit.
    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)

    assert bot.edits, "expected an inline message edit during the add flow"
    callback_data = _all_callback_data(bot.edits[-1].reply_markup)
    assert callback_data, "inline edit had no buttons"
    assert all(data.startswith(expected_prefix) for data in callback_data), callback_data
