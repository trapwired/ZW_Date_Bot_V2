"""Role-aware 'getting started' guide, sent right after the WELCOME message so a
fresh user immediately knows how to use the bot.

Text on purpose (no screenshots): never goes stale with menu changes, no asset
pipeline, ready for per-user i18n later. docs/onboarding-guide.md carries the same
content as copy-paste material for group posts (existing members won't re-/start).
"""
from Enums.Role import Role

from Utils import Format


def build_guide(role: Role, team_name: str) -> str:
    if role is Role.SPECTATOR:
        return _spectator_guide(team_name)
    guide = _player_guide(team_name)
    if role is Role.ADMIN:
        guide += _admin_addendum()
    return guide


def _player_guide(team_name: str) -> str:
    return (f'Here is how you get around the {Format.escape(team_name)} manager 🧭\n\n'
            f'📅 {Format.bold("Events")} - tap {Format.code("events")} in the keyboard below to see '
            'upcoming games, trainings and timekeeping duties. Open one and answer with '
            'Yes / No / Unsure - keeping that answer current is all the bot ever asks of you.\n\n'
            f'🔔 {Format.bold("Reminders")} - no answer yet for an upcoming event? The bot sends you '
            'a private reminder ahead of time. Answer once and it stays quiet.\n\n'
            f'📆 {Format.bold("Calendar")} - every event card has a calendar button that sends the '
            'event as a file for your phone\'s calendar app.\n\n'
            f'🌐 {Format.bold("Website")} - tap {Format.code("website")} for the team\'s page.\n\n'
            f'❓ /help shows everything you can do; /privacy explains what data the bot keeps.')


def _spectator_guide(team_name: str) -> str:
    return (f'Here is how you follow {Format.escape(team_name)} 🧭\n\n'
            f'📅 {Format.bold("Events")} - tap {Format.code("events")} in the keyboard below to see '
            'upcoming games and trainings, including who has signed up.\n\n'
            f'🌐 {Format.bold("Website")} - tap {Format.code("website")} for the team\'s page.\n\n'
            f'❓ /help shows everything you can do; /privacy explains what data the bot keeps.')


def _admin_addendum() -> str:
    return (f'\n\n🛠 {Format.bold("Admin")} - tap {Format.code("admin")} for the admin panel: '
            'add events, statistics, roles, trainers, the website link and the spectator password.')
