"""Inline choice for teamless users (the REJECTED screen): join an existing team as
spectator, or set the bot up for a new team. Dedicated callback channel like the
admin (AP#...) and roles (ROLES#...) menus; NodeHandler routes on PREFIX."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from localization.Translator import t

PREFIX = 'ONB'
DELIMITER = '#'

SPECTATOR = 'S'  # explain the spectator-password entry
NEW_TEAM = 'T'   # explain how to set the bot up for a new team
HOME = 'H'       # back to the two-way choice


def encode(action: str) -> str:
    return DELIMITER.join([PREFIX, action])


def is_onboarding_callback(data: str) -> bool:
    return data.startswith(PREFIX + DELIMITER)


def parse(data: str) -> str | None:
    if not is_onboarding_callback(data):
        return None
    return data.split(DELIMITER)[1]


def build_choice_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('🔑 Join a team as spectator'), callback_data=encode(SPECTATOR))],
        [InlineKeyboardButton(t('🆕 Set up the bot for my team'), callback_data=encode(NEW_TEAM))],
    ])
