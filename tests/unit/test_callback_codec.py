"""Pin the callback codecs (EventsMenu, AdminMenu, CallbackUtils, RoleAssignment).

The wire format is a PERSISTENCE contract: callback_data lives inside Telegram
messages already delivered to users, so a merge must reproduce these exact strings
or old buttons stop working. Hence exact-string assertions, not just round-trips.
"""
from Enums.Event import Event
from Enums.EventField import EventField
from Enums.AttendanceState import AttendanceState
from Enums.Role import Role

from Utils import CallbackUtils
from features.events import EventsMenu
from features.adminpanel import AdminMenu
from features.roles import RoleAssignment


# --- events codec (EventsMenu) -----------------------------------------------

def test_events_callback_exact_wire_format():
    assert EventsMenu.encode_list(Event.GAME) == "EV#L#0"
    assert EventsMenu.encode_card(Event.TRAINING, "doc7") == "EV#C#1#doc7"
    assert EventsMenu.encode_attend(Event.GAME, "doc7", AttendanceState.YES) == "EV#A#0#doc7#1"
    assert EventsMenu.encode_calendar(Event.TIMEKEEPING, "doc7") == "EV#I#2#doc7"
    assert EventsMenu.encode_edit_field(Event.GAME, "doc7", EventField.LOCATION) == "EV#F#0#doc7#20"
    assert EventsMenu.encode_delete_confirmed(Event.GAME, "doc7") == "EV#X#0#doc7"


def test_events_callback_roundtrip():
    encoded = EventsMenu.encode_attend(Event.TRAINING, "abc", AttendanceState.NO)
    assert EventsMenu.parse(encoded) == (EventsMenu.ATTEND, Event.TRAINING, ["abc", str(int(AttendanceState.NO))])


def test_events_callback_rejects_malformed():
    assert EventsMenu.parse("EV#L") is None            # missing event type
    assert EventsMenu.parse("EV#L#nope") is None       # non-numeric event type
    assert EventsMenu.parse("ROLES#H") is None         # different channel


# --- legacy attendance buttons (pre-redesign messages) ------------------------

def test_legacy_attendance_data_translates_to_attend_action():
    # This exact format sits on reminder/notification messages already delivered
    # to players - it must keep resolving.
    assert EventsMenu.is_legacy_attendance_callback("EDIT#GAME#YES#doc7") is True
    assert EventsMenu.try_parse_legacy_attendance("EDIT#GAME#YES#doc7") == (
        EventsMenu.ATTEND, Event.GAME, ["doc7", str(int(AttendanceState.YES))])
    assert EventsMenu.try_parse_legacy_attendance("EDIT#TRAINING#CALENDAR#doc7") == (
        EventsMenu.CALENDAR, Event.TRAINING, ["doc7"])


def test_legacy_attendance_rejects_other_old_formats():
    assert EventsMenu.try_parse_legacy_attendance("EDIT#GAME#YES") is None
    assert EventsMenu.try_parse_legacy_attendance("EDIT#NOPE#YES#doc7") is None
    assert EventsMenu.is_legacy_attendance_callback("ADMIN_UPDATE#GAME#YES#doc7") is False


# --- admin menu codec (AdminMenu) ---------------------------------------------

def test_admin_menu_exact_wire_format():
    assert AdminMenu.encode(AdminMenu.PANEL) == "AP#P"
    assert AdminMenu.encode(AdminMenu.ADD_CHOOSER, int(Event.GAME)) == "AP#A#0"
    assert AdminMenu.encode(AdminMenu.STATS_MENU, AdminMenu.REMINDER_STATISTICS) == "AP#S#REM"
    assert AdminMenu.encode(AdminMenu.WIZARD_SAVE) == "AP#ZS"


def test_admin_menu_detection_and_parse():
    assert AdminMenu.is_admin_menu_callback("AP#P") is True
    assert AdminMenu.is_admin_menu_callback("EV#L#0") is False
    assert AdminMenu.parse("AP#A#0") == (AdminMenu.ADD_CHOOSER, ["0"])
    assert AdminMenu.parse("EV#L#0") is None


# --- field-edit context (CallbackUtils.additional_info) ------------------------

def test_additional_information_roundtrip_and_format():
    built = CallbackUtils.build_additional_information(5, 10, "d1", Event.GAME, EventField.LOCATION,
                                                       prompt_message_id=77)
    assert built == "5#10#d1#0#20#77"
    assert CallbackUtils.try_parse_additional_information(built) == \
        (5, 10, "d1", Event.GAME, EventField.LOCATION, 77)
    # Contexts stashed before the prompt id existed have 5 fields and must keep parsing.
    assert CallbackUtils.try_parse_additional_information("5#10#d1#0#20") == \
        (5, 10, "d1", Event.GAME, EventField.LOCATION, None)
    assert CallbackUtils.try_parse_additional_information("5#10#d1") is None  # ancient 3-field format
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
