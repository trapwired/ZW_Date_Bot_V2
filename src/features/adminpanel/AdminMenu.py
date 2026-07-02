"""Inline admin menu: one message the admin navigates through (add event, statistics,
roles, website). Dedicated callback channel, kept separate from the events (EV#...)
and roles (ROLES#...) channels; NodeHandler routes on PREFIX. The roles button jumps
straight into the existing roles channel."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from Enums.Event import Event

from features.roles import RoleAssignment

from Utils import Format

PREFIX = 'AP'
DELIMITER = '#'

PANEL_TEXT = Format.bold('Admin menu') + '\nAdd events, look at statistics, manage roles or set the website link.'

# Actions (kept short to stay well under Telegram's 64-byte callback_data limit).
PANEL = 'P'             # (re-)show the admin menu home
ADD_CHOOSER = 'A'       # choose which event type to add; with an arg: start that wizard
STATS_MENU = 'S'        # choose which statistics to show; with an arg: render them
RESET_CONFIRM = 'RC'    # ask before resetting the season statistics
RESET_CONFIRMED = 'RY'  # reset the season statistics
WEBSITE_PROMPT = 'W'    # start typing a new website URL
WEBSITE_YES = 'WY'      # commit the typed URL
WEBSITE_NO = 'WN'       # discard the typed URL
WIZARD_CANCEL = 'ZC'    # add-event wizard: discard the draft
WIZARD_RESTART = 'ZR'   # add-event wizard: discard and start over
WIZARD_SAVE = 'ZS'      # add-event wizard: persist the finished draft

REMINDER_STATISTICS = 'REM'  # STATS_MENU arg for the reminder statistics (others are Event ints)

ADD_LABELS = {Event.GAME: 'Game', Event.TRAINING: 'Training', Event.TIMEKEEPING: 'Timekeeping'}
STATS_LABELS = {Event.GAME: 'Games', Event.TRAINING: 'Trainings', Event.TIMEKEEPING: 'Timekeeping'}


def encode(action: str, *args) -> str:
    return DELIMITER.join([PREFIX, action, *[str(a) for a in args]])


def is_admin_menu_callback(data: str) -> bool:
    return data.startswith(PREFIX + DELIMITER)


def parse(data: str) -> tuple[str, list[str]] | None:
    if not is_admin_menu_callback(data):
        return None
    parts = data.split(DELIMITER)
    if len(parts) < 2:
        return None
    return parts[1], parts[2:]


###########
# MARKUPS #
###########

def build_panel_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ Add event', callback_data=encode(ADD_CHOOSER)),
         InlineKeyboardButton('📊 Statistics', callback_data=encode(STATS_MENU))],
        [InlineKeyboardButton('👥 Roles', callback_data=RoleAssignment.encode_home()),
         InlineKeyboardButton('🌐 Set website', callback_data=encode(WEBSITE_PROMPT))],
    ])


def build_add_chooser_markup() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(label, callback_data=encode(ADD_CHOOSER, int(event_type)))
             for event_type, label in ADD_LABELS.items()]]
    rows.append([InlineKeyboardButton('« Back', callback_data=encode(PANEL))])
    return InlineKeyboardMarkup(rows)


def build_stats_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('Reminders', callback_data=encode(STATS_MENU, REMINDER_STATISTICS))],
        [InlineKeyboardButton(label, callback_data=encode(STATS_MENU, int(event_type)))
         for event_type, label in STATS_LABELS.items()],
        [InlineKeyboardButton('⚠️ End season (reset statistics)', callback_data=encode(RESET_CONFIRM))],
        [InlineKeyboardButton('« Back', callback_data=encode(PANEL))],
    ])


def build_back_to_stats_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('« Back to statistics', callback_data=encode(STATS_MENU))]])


def build_reset_confirm_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('Yes, end the season', callback_data=encode(RESET_CONFIRMED))],
        [InlineKeyboardButton('« Back', callback_data=encode(STATS_MENU))],
    ])


def build_wizard_markup(can_save: bool) -> InlineKeyboardMarkup:
    buttons = []
    if can_save:
        buttons.append(InlineKeyboardButton('SAVE', callback_data=encode(WIZARD_SAVE)))
    buttons.append(InlineKeyboardButton('RESTART', callback_data=encode(WIZARD_RESTART)))
    buttons.append(InlineKeyboardButton('CANCEL', callback_data=encode(WIZARD_CANCEL)))
    return InlineKeyboardMarkup([buttons])


def build_website_confirm_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('💾 Save', callback_data=encode(WEBSITE_YES)),
         InlineKeyboardButton('Cancel', callback_data=encode(WEBSITE_NO))],
    ])


def build_website_prompt_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('Cancel', callback_data=encode(PANEL))]])


def build_back_to_panel_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('« Back', callback_data=encode(PANEL))]])
