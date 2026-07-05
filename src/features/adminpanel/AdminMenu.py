"""Inline admin menu: one message the admin navigates through (add event, statistics,
roles, website). Dedicated callback channel, kept separate from the events (EV#...)
and roles (ROLES#...) channels; NodeHandler routes on PREFIX. The roles button jumps
straight into the existing roles channel."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from Enums.Event import Event

from features.roles import RoleAssignment
from framework import TeamStamp

from localization.Languages import NATIVE_NAMES, SUPPORTED_LANGUAGES
from localization.Translator import t

PREFIX = 'AP'
DELIMITER = '#'

PANEL_TEXT = ('<b>Admin menu</b>'
              '\nAdd events, look at statistics, manage roles, send an announcement - '
              'or open the spectator and setup sections.')

# Actions (kept short to stay well under Telegram's 64-byte callback_data limit).
PANEL = 'P'             # (re-)show the admin menu home
ADD_CHOOSER = 'A'       # choose which event type to add; with an arg: start that wizard
STATS_MENU = 'S'        # choose which statistics to show; with an arg: render them
RESET_CONFIRM = 'RC'    # ask before resetting the season statistics
RESET_CONFIRMED = 'RY'  # reset the season statistics
WEBSITE_PROMPT = 'W'    # start typing a new website URL
WEBSITE_YES = 'WY'      # commit the typed URL
WEBSITE_NO = 'WN'       # discard the typed URL
SPECTATOR_PASSWORD_PROMPT = 'K'   # K as in key/Kennwort ('S'/'P' were taken)   # start typing a new spectator password
SPECTATOR_PASSWORD_SAVE = 'KY'    # commit the typed spectator password
SPECTATOR_PASSWORD_CANCEL = 'KN'  # discard the typed spectator password
TRAINERS_MENU = 'T'     # show the trainer-routing overview
TRAINERS_LIST = 'TL'    # arg: event group (Event int) - show the toggle list for it
TRAINERS_TOGGLE = 'TX'  # args: event group + telegram id - flip that person's trainer flag
TEAM_NAME_PROMPT = 'M'   # M as in Mannschaft - start typing a new team name
TEAM_NAME_SAVE = 'MY'    # commit the typed team name
TEAM_NAME_CANCEL = 'MN'  # discard the typed team name
SPECTATOR_INVITE = 'I'   # mint a one-time spectator invite link
SPECTATORS_MENU = 'V'    # V as in viewers - the spectator section (password + invites)
SETUP_MENU = 'U'         # rarely-touched team configuration (name, website, trainers)
TEAM_LANGUAGE_MENU = 'G'  # G as in Gruppensprache - pick the team (group-chat) language
TEAM_LANGUAGE_SET = 'GS'  # arg: language code - set the team language
ANNOUNCE_PROMPT = 'N'         # start typing an announcement
ANNOUNCE_TO_PLAYERS = 'NP'    # send the staged announcement to every player privately
ANNOUNCE_TO_GROUP = 'NG'      # post the staged announcement in the team group chat
WIZARD_CANCEL = 'ZC'    # add-event wizard: discard the draft
WIZARD_RESTART = 'ZR'   # add-event wizard: discard and start over
WIZARD_SAVE = 'ZS'      # add-event wizard: persist the finished draft

REMINDER_STATISTICS = 'REM'  # STATS_MENU arg for the reminder statistics (others are Event ints)

ADD_LABELS = {Event.GAME: 'Game', Event.TRAINING: 'Training', Event.TIMEKEEPING: 'Timekeeping'}
STATS_LABELS = {Event.GAME: 'Games', Event.TRAINING: 'Trainings', Event.TIMEKEEPING: 'Timekeeping'}
# Trainer routing knows two lists (Team.trainer_chat_ids): GAME covers timekeeping too.
TRAINER_GROUP_LABELS = {Event.GAME: '🥅 Games & timekeeping', Event.TRAINING: '🏃 Trainings'}


def encode(action: str, *args) -> str:
    return TeamStamp.stamp(DELIMITER.join([PREFIX, action, *[str(a) for a in args]]))


def is_admin_menu_callback(data: str) -> bool:
    return data.startswith(PREFIX + DELIMITER)


def parse(data: str) -> tuple[str, list[str]] | None:
    if not is_admin_menu_callback(data):
        return None
    parts = TeamStamp.strip(data).split(DELIMITER)
    if len(parts) < 2:
        return None
    return parts[1], parts[2:]


###########
# MARKUPS #
###########

def build_panel_markup() -> InlineKeyboardMarkup:
    # Frequent actions stay top-level; rare configuration nests in the two sections.
    # Max 2 buttons per row: 3-way rows truncate the longer labels on phones.
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('➕ Add event'), callback_data=encode(ADD_CHOOSER)),
         InlineKeyboardButton(t('📊 Statistics'), callback_data=encode(STATS_MENU))],
        [InlineKeyboardButton(t('👥 Roles'), callback_data=RoleAssignment.encode_home()),
         InlineKeyboardButton(t('📣 Announce'), callback_data=encode(ANNOUNCE_PROMPT))],
        [InlineKeyboardButton(t('👁 Spectators'), callback_data=encode(SPECTATORS_MENU)),
         InlineKeyboardButton(t('⚙️ Setup'), callback_data=encode(SETUP_MENU))],
    ])


def build_spectators_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('🔑 Set password'), callback_data=encode(SPECTATOR_PASSWORD_PROMPT))],
        [InlineKeyboardButton(t('🔗 One-time invite link'), callback_data=encode(SPECTATOR_INVITE))],
        [InlineKeyboardButton(t('« Back'), callback_data=encode(PANEL))],
    ])


def build_setup_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('✏️ Team name'), callback_data=encode(TEAM_NAME_PROMPT))],
        [InlineKeyboardButton(t('🌐 Website'), callback_data=encode(WEBSITE_PROMPT))],
        [InlineKeyboardButton(t('🧑‍🏫 Trainers'), callback_data=encode(TRAINERS_MENU))],
        [InlineKeyboardButton(t('🗣 Team language'), callback_data=encode(TEAM_LANGUAGE_MENU))],
        [InlineKeyboardButton(t('« Back'), callback_data=encode(PANEL))],
    ])


def build_team_language_markup(current_language: str) -> InlineKeyboardMarkup:
    # Native names on purpose (like the /language picker): recognizable in any language.
    rows = [[InlineKeyboardButton(('✅ ' if language == current_language else '') + NATIVE_NAMES[language],
                                  callback_data=encode(TEAM_LANGUAGE_SET, language))]
            for language in SUPPORTED_LANGUAGES]
    rows.append([InlineKeyboardButton(t('« Back'), callback_data=encode(SETUP_MENU))])
    return InlineKeyboardMarkup(rows)


def build_team_name_confirm_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('💾 Save'), callback_data=encode(TEAM_NAME_SAVE)),
         InlineKeyboardButton(t('Cancel'), callback_data=encode(TEAM_NAME_CANCEL))],
    ])


def build_announce_confirm_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('📨 To every player privately'), callback_data=encode(ANNOUNCE_TO_PLAYERS))],
        [InlineKeyboardButton(t('👥 To the group chat'), callback_data=encode(ANNOUNCE_TO_GROUP))],
        [InlineKeyboardButton(t('Cancel'), callback_data=encode(PANEL))],
    ])


def build_trainers_menu_markup() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(t(TRAINER_GROUP_LABELS[event_type]),
                                  callback_data=encode(TRAINERS_LIST, int(event_type)))]
            for event_type in TRAINER_GROUP_LABELS]
    rows.append([InlineKeyboardButton(t('« Back'), callback_data=encode(SETUP_MENU))])
    return InlineKeyboardMarkup(rows)


def build_trainer_toggle_markup(event_type: Event, entries: list[tuple[int, str]],
                                trainer_ids: list[int]) -> InlineKeyboardMarkup:
    # entries: (telegram_id, display_name) - one full-width toggle row per person.
    rows = [[InlineKeyboardButton(f'{"✅" if telegram_id in trainer_ids else "▫️"} {name}',
                                  callback_data=encode(TRAINERS_TOGGLE, int(event_type), telegram_id))]
            for telegram_id, name in entries]
    rows.append([InlineKeyboardButton(t('« Back'), callback_data=encode(TRAINERS_MENU))])
    return InlineKeyboardMarkup(rows)


def build_add_chooser_markup() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(t(ADD_LABELS[event_type]), callback_data=encode(ADD_CHOOSER, int(event_type)))
             for event_type in ADD_LABELS]]
    rows.append([InlineKeyboardButton(t('« Back'), callback_data=encode(PANEL))])
    return InlineKeyboardMarkup(rows)


def build_stats_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('Reminders'), callback_data=encode(STATS_MENU, REMINDER_STATISTICS))],
        [InlineKeyboardButton(t(STATS_LABELS[event_type]), callback_data=encode(STATS_MENU, int(event_type)))
         for event_type in STATS_LABELS],
        [InlineKeyboardButton(t('⚠️ End season (reset statistics)'), callback_data=encode(RESET_CONFIRM))],
        [InlineKeyboardButton(t('« Back'), callback_data=encode(PANEL))],
    ])


def build_back_to_stats_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t('« Back to statistics'), callback_data=encode(STATS_MENU))]])


def build_reset_confirm_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('Yes, end the season'), callback_data=encode(RESET_CONFIRMED))],
        [InlineKeyboardButton(t('« Back'), callback_data=encode(STATS_MENU))],
    ])


def build_wizard_markup(can_save: bool) -> InlineKeyboardMarkup:
    buttons = []
    if can_save:
        buttons.append(InlineKeyboardButton(t('SAVE'), callback_data=encode(WIZARD_SAVE)))
    buttons.append(InlineKeyboardButton(t('RESTART'), callback_data=encode(WIZARD_RESTART)))
    buttons.append(InlineKeyboardButton(t('CANCEL'), callback_data=encode(WIZARD_CANCEL)))
    return InlineKeyboardMarkup([buttons])


def build_website_confirm_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('💾 Save'), callback_data=encode(WEBSITE_YES)),
         InlineKeyboardButton(t('Cancel'), callback_data=encode(WEBSITE_NO))],
    ])


def build_spectator_password_confirm_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('💾 Save'), callback_data=encode(SPECTATOR_PASSWORD_SAVE)),
         InlineKeyboardButton(t('Cancel'), callback_data=encode(SPECTATOR_PASSWORD_CANCEL))],
    ])


def build_typed_input_prompt_markup(back_action: str = None) -> InlineKeyboardMarkup:
    # Cancel returns to the section the flow was launched from (default: panel root).
    return InlineKeyboardMarkup([[InlineKeyboardButton(t('Cancel'), callback_data=encode(back_action or PANEL))]])


def build_back_markup(back_action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t('« Back'), callback_data=encode(back_action))]])


def build_back_to_panel_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t('« Back'), callback_data=encode(PANEL))]])
