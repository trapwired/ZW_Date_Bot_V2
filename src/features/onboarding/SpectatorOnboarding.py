"""Shared spectator-entry mechanics for the two teamless nodes.

A spectator can join via the team's password (typed on the REJECTED screen) or a
one-time invite deep link (t.me/<bot>?start=<token>, arriving as '/start <token>'
in whatever state the user is in) - both paths converge here so the join + welcome
sequence cannot drift between them.
"""
from Enums.MessageType import MessageType
from Enums.Role import Role
from Enums.UserState import UserState

from features.onboarding import WelcomeGuide


def extract_start_token(text: str) -> str | None:
    """The deep-link payload of a '/start <token>' message, None for a bare /start
    or any other text."""
    parts = text.split(maxsplit=1)
    # Command matching is case-insensitive (like the transition router); the token
    # itself stays case-sensitive.
    if len(parts) == 2 and parts[0].split('@')[0].lower() == '/start':
        return parts[1].strip()
    return None


async def join_as_spectator(node, update, user_to_state, team) -> None:
    """THE spectator entry: stamp the team (join_team seam), then welcome + guide -
    identical for the password and the invite-link path. Callers guarantee the user
    is teamless (a team member redeeming a link would be re-roled)."""
    user_to_state.additional_info = ''   # a successful entry clears any attempt record
    node.user_state_service.join_team(user_to_state, team.doc_id, Role.SPECTATOR)
    await send_welcome_and_guide(node, update, user_to_state, team)


async def send_welcome_and_guide(node, update, user_to_state, team) -> None:
    """The two-message onboarding tail (WELCOME + getting-started guide) - one
    sequence for players, admins and spectators so the paths can't drift."""
    await node.telegram_service.send_message(
        update=update,
        all_buttons=node.get_commands_for_buttons(user_to_state.role, UserState.DEFAULT),
        message_type=MessageType.WELCOME,
        message_extra_text=team.name)
    await node.telegram_service.send_message(
        update=update,
        all_buttons=None,
        message=WelcomeGuide.build_guide(user_to_state.role, team.name))
