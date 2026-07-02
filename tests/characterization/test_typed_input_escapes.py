"""Characterization: typed-input states can't strand the user.

The main-menu keyboard stays visible during typed input (wizard, field edit, URL);
pressing one of its entries escapes the flow - cleanup runs (draft/context dropped)
and the command executes as if the user were already on the main menu.
"""
import pytest

from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.EventField import EventField
from features.adminpanel import AdminMenu
from Utils import CallbackUtils
from Utils.CustomExceptions import NoTempDataFoundException
from tests.helpers import drive, drive_callback, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 1500


async def test_events_escapes_the_add_wizard_and_discards_the_draft(node_handler, data_access, bot, game):
    uts = seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ADD_CHOOSER, int(Event.GAME)))
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_EVENT

    await drive(node_handler, ADMIN_ID, "Events")

    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT
    with pytest.raises(NoTempDataFoundException):
        data_access.get_temp_data(uts.user_id)
    # The events list actually opened (an inline markup went out last).
    assert [m for m in bot.sent if m.chat_id == ADMIN_ID][-1].reply_markup is not None
    assert_no_error_reported(bot)


async def test_admin_escapes_the_field_edit_and_clears_context(node_handler, data_access, bot, game):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_EVENT_FIELD,
              additional_info=CallbackUtils.build_additional_information(
                  1, ADMIN_ID, game.doc_id, Event.GAME, EventField.LOCATION))

    await drive(node_handler, ADMIN_ID, "Admin")

    state = data_access.get_user_state(ADMIN_ID)
    assert state.state == UserState.DEFAULT
    assert state.additional_info == ''
    assert any("Admin menu" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_website_escapes_the_url_input(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_WEBSITE, additional_info="staged")

    await drive(node_handler, ADMIN_ID, "events")

    state = data_access.get_user_state(ADMIN_ID)
    assert state.state == UserState.DEFAULT
    assert state.additional_info == ''
    assert_no_error_reported(bot)


async def test_admin_menu_back_button_resets_a_typed_input_state(node_handler, data_access, bot):
    # Pressing 'Back' on the admin menu message while a typed input is pending is the
    # inline escape hatch: staged input is dropped, state returns to the main menu.
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_WEBSITE, additional_info="staged")

    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.PANEL))

    state = data_access.get_user_state(ADMIN_ID)
    assert state.state == UserState.DEFAULT
    assert state.additional_info == ''
    assert_no_error_reported(bot)
