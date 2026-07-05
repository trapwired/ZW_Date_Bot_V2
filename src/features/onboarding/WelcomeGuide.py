"""Role-aware 'getting started' guide, sent right after the WELCOME message so a
fresh user immediately knows how to use the bot.

Text on purpose (no screenshots): never goes stale with menu changes, no asset
pipeline, ready for per-user i18n later. docs/onboarding-guide.md carries the same
content as copy-paste material for group posts (existing members won't re-/start).
"""
from Enums.Role import Role

from localization.Translator import t

from Utils import Format


def build_guide(role: Role, team_name: str) -> str:
    if role is Role.SPECTATOR:
        return _spectator_guide(team_name)
    guide = _player_guide(team_name)
    if role is Role.ADMIN:
        guide += _admin_addendum()
    return guide


def _player_guide(team_name: str) -> str:
    return t('Here is how you get around the {team} manager 🧭\n\n'
             '📅 <b>Events</b> - tap <code>events</code> in the keyboard below to see '
             'upcoming games, trainings and timekeeping duties. Open one and answer with '
             'Yes / No / Unsure - keeping that answer current is all the bot ever asks of you.\n\n'
             '🔔 <b>Reminders</b> - no answer yet for an upcoming event? The bot sends you '
             'a private reminder ahead of time. Answer once and it stays quiet.\n\n'
             '📆 <b>Calendar</b> - every event card has a calendar button that sends the '
             'event as a file for your phone\'s calendar app.\n\n'
             '🌐 <b>Website</b> - tap <code>website</code> for the team\'s page.\n\n'
             '❓ /help shows everything you can do; /privacy explains what data the bot keeps.',
             team=Format.escape(team_name))


def _spectator_guide(team_name: str) -> str:
    return t('Here is how you follow {team} 🧭\n\n'
             '📅 <b>Events</b> - tap <code>events</code> in the keyboard below to see '
             'upcoming games and trainings, including who has signed up.\n\n'
             '🌐 <b>Website</b> - tap <code>website</code> for the team\'s page.\n\n'
             '❓ /help shows everything you can do; /privacy explains what data the bot keeps.',
             team=Format.escape(team_name))


def build_admin_setup_guide(team_name: str) -> str:
    """Sent to the group admin right after adding the bot registered their team."""
    return t('🎉 <b>{team}</b> is registered, and you are its first admin!\n\n'
             'Your setup steps - everything lives behind the admin menu '
             '(tap <code>admin</code> in the keyboard below):\n\n'
             '1️⃣ <b>Spectators</b> - set a password (🔑) fans enter to follow the team, '
             'or hand out one-time invite links (🔗).\n'
             '2️⃣ <b>First event</b> (➕) - add a game or training so there is something '
             'to answer to.\n'
             '3️⃣ <b>Invite the team</b> - tell everyone in the group chat to open a '
             'private chat with me and press Start; group members join as players automatically.\n'
             '4️⃣ Optional: <b>trainers</b> (🧑‍🏫) for summaries and warnings, the '
             '<b>website</b> (🌐) link, and a different <b>team name</b> (✏️) - '
             'I took it from your group title.\n\n'
             'Changed your mind? Just remove me from the group chat and everything is rolled back.',
             team=Format.escape(team_name))


def _admin_addendum() -> str:
    return t('\n\n🛠 <b>Admin</b> - tap <code>admin</code> for the admin panel: '
             'add events, statistics, roles, trainers, the website link and the spectator password.')
