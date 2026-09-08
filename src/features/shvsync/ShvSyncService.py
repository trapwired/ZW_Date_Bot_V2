"""Daily sync of the games table against the SHV matchcenter schedule.

Runs for every team that has an SHV team id in its settings (shv_team_id, set by
an admin); teams without one are skipped, so the sync is off until configured.
New games are imported, moved/relocated games updated in place (attendance
answers survive - the game row keeps its id), and the game trainers are notified
of every change. Nothing is ever deleted automatically."""
from telegram.ext import ContextTypes

from data.DataAccess import DataAccess

from framework.TeamIteration import for_each_team
from framework.Services.TelegramService import TelegramService

from features.shvsync import ShvApiClient
from features.shvsync import GameSyncPlanner
from features.shvsync.GameSyncPlanner import SyncPlan, GameUpdate

from Enums.Event import Event

from localization.Translator import t

from Utils import DateTimeUtils
from Utils import Format
from Utils import PrintUtils


class ShvSyncService:

    def __init__(self, data_access: DataAccess, telegram_service: TelegramService):
        self.data_access = data_access
        self.telegram_service = telegram_service

    async def sync_all_teams(self, context: ContextTypes.DEFAULT_TYPE):
        await for_each_team(self.data_access, self.telegram_service, self._sync_current_team)

    async def _sync_current_team(self):
        shv_team_id = self.data_access.get_shv_team_id()
        if shv_team_id is None:
            return

        shv_games = await ShvApiClient.fetch_games(shv_team_id)
        now = DateTimeUtils.get_local_now()
        # Only upcoming games: the bot's schedule is forward-looking, and syncing
        # history would touch games whose attendance answers are already settled.
        upcoming = [game for game in shv_games if not game.is_played and game.timestamp > now]

        sync_plan = GameSyncPlanner.plan(upcoming, self.data_access.get_ordered_games())
        for game in sync_plan.to_add:
            self.data_access.add(game)
        for update in sync_plan.to_update:
            self.data_access.update(update.game)

        if sync_plan.has_changes():
            await self.telegram_service.send_info_message_to_trainers(
                _build_report(sync_plan), Event.GAME)


def _build_report(sync_plan: SyncPlan) -> str:
    parts = [t('📅 <b>SHV schedule update</b> (handball.ch)')]
    for game in sync_plan.to_add:
        parts.append(t('New game:') + '\n' + PrintUtils.pretty_print_long(game))
    for update in sync_plan.to_update:
        parts.append(t('Game changed:') + '\n'
                     + _old_game_line(update) + '\n→ ' + PrintUtils.pretty_print_long(update.game))
    for game in sync_plan.vanished:
        parts.append(t('Game no longer on the SHV schedule - if it was cancelled, '
                       'please delete it in the bot:') + '\n' + PrintUtils.pretty_print_long(game))
    return '\n\n'.join(parts)


def _old_game_line(update: GameUpdate) -> str:
    return (Format.bold(update.old_timestamp.strftime(PrintUtils.DATETIME_FORMAT))
            + ' | ' + Format.escape(update.old_location.title()))
