"""Pin the two callback codecs Phase 1 merges into one.

The wire format is a PERSISTENCE contract: callback_data lives inside Telegram
messages already delivered to users, so a merge must reproduce these exact strings
or old buttons stop working. Hence exact-string assertions, not just round-trips.
"""
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption
from Enums.Role import Role

from Utils import CallbackUtils
from features.roles import RoleAssignment


# --- event-attendance codec (CallbackUtils) ---------------------------------

def test_event_callback_exact_wire_format():
    assert CallbackUtils.get_callback_message(
        UserState.EDIT, Event.GAME, CallbackOption.YES, "doc7") == "EDIT#GAME#YES#doc7"


def test_event_callback_roundtrip():
    encoded = CallbackUtils.get_callback_message(
        UserState.ADMIN_UPDATE, Event.TRAINING, CallbackOption.DATETIME, "abc")
    assert CallbackUtils.try_parse_callback_message(encoded) == (
        UserState.ADMIN_UPDATE, Event.TRAINING, CallbackOption.DATETIME, "abc")


def test_event_callback_rejects_malformed():
    assert CallbackUtils.try_parse_callback_message("only#three#parts") is None
    assert CallbackUtils.try_parse_callback_message("NOPE#GAME#YES#x") is None  # unknown UserState


def test_additional_information_roundtrip_and_format():
    built = CallbackUtils.build_additional_information(5, 10, "d1", Event.GAME, CallbackOption.LOCATION)
    assert built == "5#10#d1#0#20"
    assert CallbackUtils.try_parse_additional_information(built) == (5, 10, "d1", Event.GAME, CallbackOption.LOCATION)
    assert CallbackUtils.try_parse_additional_information("5#10#d1") is None  # pre-3b 3-field format
    assert CallbackUtils.try_parse_additional_information("bad") is None


# --- role-assignment codec (RoleAssignment) ---------------------------------

def test_role_callback_exact_wire_format():
    assert RoleAssignment.encode_list_users(Role.PLAYER) == "ROLES#R#0"
    assert RoleAssignment.encode_select_user("u1") == "ROLES#U#u1"
    assert RoleAssignment.encode_assign("u1", Role.ADMIN) == "ROLES#A#u1#42"
    assert RoleAssignment.encode_home() == "ROLES#H"


def test_role_callback_detection_and_parse():
    assert RoleAssignment.is_role_callback("ROLES#A#u1#42") is True
    assert RoleAssignment.is_role_callback("EDIT#GAME#YES#x") is False
    assert RoleAssignment.parse("ROLES#A#u1#42") == ("A", ["u1", "42"])
    assert RoleAssignment.parse("EDIT#GAME#YES#x") is None
