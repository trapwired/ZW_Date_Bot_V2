from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from Enums.Role import Role, ASSIGNABLE_ROLES

from framework import TeamStamp

from localization.Translator import t

# Dedicated callback channel for the roles slice, kept separate from the
# event-attendance callback format (UserState#Event#CallbackOption#doc_id) so the
# two domains don't have to share an encoding. NodeHandler routes on PREFIX.
PREFIX = 'ROLES'
DELIMITER = '#'

# Actions (kept short to stay well under Telegram's 64-byte callback_data limit).
LIST_USERS = 'R'    # show users that currently hold a role bucket
LIST_ADMINS = 'D'   # show users holding the admin flag
SELECT_USER = 'U'   # show assignable roles + admin toggle for one user
ASSIGN = 'A'        # write a new role to one user
TOGGLE_ADMIN = 'T'  # flip one user's admin flag
HOME = 'H'          # back to the role overview

ADMIN_MARKER = '⭐'

# Origin token carried on SELECT_USER so the assign screen's Back button returns to
# the list the user actually came from: the admin list, or a role bucket (role int).
FROM_ADMIN_LIST = LIST_ADMINS


@dataclass(frozen=True)
class UserListEntry:
    user_doc_id: str
    display_name: str
    role: Role
    is_admin: bool

    def label(self) -> str:
        label = t('{name} ({role})', name=self.display_name, role=self.role.name)
        return f'{label} {ADMIN_MARKER}' if self.is_admin else label


def _encode(action: str, *args) -> str:
    # THE encoder: every button goes through here so none can miss the team stamp.
    return TeamStamp.stamp(DELIMITER.join([PREFIX, action, *[str(a) for a in args]]))


def encode_list_users(role: Role) -> str:
    return _encode(LIST_USERS, int(role))


def encode_list_admins() -> str:
    return _encode(LIST_ADMINS)


def encode_select_user(user_doc_id: str, origin: str) -> str:
    return _encode(SELECT_USER, user_doc_id, origin)


def encode_assign(user_doc_id: str, new_role: Role) -> str:
    return _encode(ASSIGN, user_doc_id, int(new_role))


def encode_toggle_admin(user_doc_id: str) -> str:
    return _encode(TOGGLE_ADMIN, user_doc_id)


def encode_home() -> str:
    return _encode(HOME)


def encode_origin_list(origin: str | None, fallback_role: Role) -> str:
    """The callback of the list an assign screen was opened from; pre-refactor
    SELECT_USER buttons carry no origin and fall back to the user's role bucket."""
    if origin == FROM_ADMIN_LIST:
        return encode_list_admins()
    return encode_list_users(Role(int(origin)) if origin else fallback_role)


def is_role_callback(data: str) -> bool:
    return data.startswith(PREFIX + DELIMITER)


def parse(data: str) -> tuple[str, list[str]] | None:
    if not is_role_callback(data):
        return None
    parts = TeamStamp.strip(data).split(DELIMITER)
    if len(parts) < 2:
        return None
    return parts[1], parts[2:]


def build_overview_markup(counts: dict[Role, int], admin_count: int,
                          back_callback_data: str = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(t('{role} ({count})', role=role.name, count=counts[role]),
                                  callback_data=encode_list_users(role))]
            for role in ASSIGNABLE_ROLES]
    rows.append([InlineKeyboardButton(t('{marker} ADMIN ({count})', marker=ADMIN_MARKER, count=admin_count),
                                      callback_data=encode_list_admins())])
    if back_callback_data:
        # Caller-supplied so this slice needs no knowledge of the menu it is embedded in
        # (the admin menu passes its own panel callback here).
        rows.append([InlineKeyboardButton(t('« Back'), callback_data=back_callback_data)])
    return InlineKeyboardMarkup(rows)


def build_user_list_markup(entries: list[UserListEntry], origin: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(entry.label(),
                                  callback_data=encode_select_user(entry.user_doc_id, origin))]
            for entry in entries]
    rows.append([InlineKeyboardButton(t('« Back'), callback_data=encode_home())])
    return InlineKeyboardMarkup(rows)


def build_assign_markup(user_doc_id: str, current_role: Role, is_admin: bool,
                        back_callback_data: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(role.name, callback_data=encode_assign(user_doc_id, role))]
            for role in ASSIGNABLE_ROLES if role != current_role]
    admin_label = (t('{marker} Remove admin', marker=ADMIN_MARKER) if is_admin
                   else t('{marker} Make admin', marker=ADMIN_MARKER))
    rows.append([InlineKeyboardButton(admin_label, callback_data=encode_toggle_admin(user_doc_id))])
    rows.append([InlineKeyboardButton(t('« Back'), callback_data=back_callback_data)])
    return InlineKeyboardMarkup(rows)


def build_home_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t('« Back to roles'), callback_data=encode_home())]])
