from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from Enums.Role import Role, ASSIGNABLE_ROLES

from framework import TeamStamp

# Dedicated callback channel for the /assign_roles slice, kept separate from the
# event-attendance callback format (UserState#Event#CallbackOption#doc_id) so the
# two domains don't have to share an encoding. NodeHandler routes on PREFIX.
PREFIX = 'ROLES'
DELIMITER = '#'

# Actions (kept short to stay well under Telegram's 64-byte callback_data limit).
LIST_USERS = 'R'   # show users that currently hold a role bucket
SELECT_USER = 'U'  # show assignable roles for one user
ASSIGN = 'A'       # write a new role to one user
HOME = 'H'         # back to the role overview


def encode_list_users(role: Role) -> str:
    return TeamStamp.stamp(DELIMITER.join([PREFIX, LIST_USERS, str(int(role))]))


def encode_select_user(user_doc_id: str) -> str:
    return TeamStamp.stamp(DELIMITER.join([PREFIX, SELECT_USER, user_doc_id]))


def encode_assign(user_doc_id: str, new_role: Role) -> str:
    return TeamStamp.stamp(DELIMITER.join([PREFIX, ASSIGN, user_doc_id, str(int(new_role))]))


def encode_home() -> str:
    return TeamStamp.stamp(DELIMITER.join([PREFIX, HOME]))


def is_role_callback(data: str) -> bool:
    return data.startswith(PREFIX + DELIMITER)


def parse(data: str) -> tuple[str, list[str]] | None:
    if not is_role_callback(data):
        return None
    parts = TeamStamp.strip(data).split(DELIMITER)
    if len(parts) < 2:
        return None
    return parts[1], parts[2:]


def build_overview_markup(counts: dict[Role, int], back_callback_data: str = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f'{role.name} ({counts[role]})', callback_data=encode_list_users(role))]
            for role in ASSIGNABLE_ROLES]
    if back_callback_data:
        # Caller-supplied so this slice needs no knowledge of the menu it is embedded in
        # (the admin menu passes its own panel callback here).
        rows.append([InlineKeyboardButton('« Back', callback_data=back_callback_data)])
    return InlineKeyboardMarkup(rows)


def build_user_list_markup(entries: list[tuple[str, str, Role]]) -> InlineKeyboardMarkup:
    # entries: (user_doc_id, display_name, current_role)
    rows = [[InlineKeyboardButton(f'{name} ({role.name})', callback_data=encode_select_user(user_doc_id))]
            for user_doc_id, name, role in entries]
    rows.append([InlineKeyboardButton('« Back', callback_data=encode_home())])
    return InlineKeyboardMarkup(rows)


def build_assign_markup(user_doc_id: str, current_role: Role) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(role.name, callback_data=encode_assign(user_doc_id, role))]
            for role in ASSIGNABLE_ROLES if role != current_role]
    rows.append([InlineKeyboardButton('« Back', callback_data=encode_list_users(current_role))])
    return InlineKeyboardMarkup(rows)


def build_home_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('« Back to roles', callback_data=encode_home())]])
