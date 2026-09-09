"""Daily sync of the games table against the SHV matchcenter schedule.

The SHV team id is derived from the team's website setting (a matchcenter team
URL like https://www.handball.ch/de/matchcenter/teams/36769): no website means
skip, a website of another shape alerts the maintainer (typo, or another portal -
the alert carries a disable button), and shv_sync_disabled turns the sync off for
a team whose portal the sync cannot read. Fetch failures also go to the
maintainer, with the website and the tried API path.

Unambiguous changes are applied automatically: a game matched by shv_game_id or
by (normalized) opponent mirrors the SHV data, players are re-asked only when the
move exceeds the attendance-reset threshold, and the admins get a report.
Everything ambiguous becomes a yes/no question to the admins (create / adopt /
delete), tracked in shv_sync_decisions so an unanswered or declined question is
not re-asked before REASK_AFTER - except 'keep this manual game' and 'these are
different games', which are final. Nothing is ever deleted without a yes."""
import secrets

import httpx
import pandas as pd

from telegram.ext import ContextTypes

from data.DataAccess import DataAccess
from data.TenantContext import current_team_id, team_context

from framework.TeamIteration import for_each_team
from framework.RecipientLanguage import recipient_language_context
from framework.Services.TelegramService import TelegramService

from features.shvsync import ShvApiClient
from features.shvsync import GameSyncPlanner
from features.shvsync import SyncMenu
from features.shvsync.GameSyncPlanner import SyncPlan, GameUpdate
from features.shvsync.ShvApiClient import ShvGame, ShvApiError
from features.eventmgmt import PlayerNotifications
from features.events import EventsMenu

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.MessageType import MessageType
from Enums.ShvSync import ShvDecisionKind, ShvDecisionStatus

from domain import AttendanceResetPolicy
from domain.entities.Game import Game
from domain.entities.ShvSyncDecision import ShvSyncDecision

from localization.Translator import t

from Utils import DateTimeUtils
from Utils import PrintUtils
from Utils.CustomExceptions import ObjectNotFoundException

# Unanswered questions are repeated, and declined create/delete/bulk questions
# re-asked (circumstances change), after this long. 'Keep manual game' and
# 'different games' answers are final and never re-asked.
REASK_AFTER = pd.Timedelta(days=14)

REPORT_HEADER = '📅 <b>SHV schedule update</b> (handball.ch)'


class ShvSyncService:

    def __init__(self, data_access: DataAccess, telegram_service: TelegramService):
        self.data_access = data_access
        self.telegram_service = telegram_service

    ############
    # SYNC JOB #
    ############

    async def sync_all_teams(self, context: ContextTypes.DEFAULT_TYPE):
        await for_each_team(self.data_access, self.telegram_service, self._sync_current_team)

    async def _sync_current_team(self):
        if self.data_access.is_shv_sync_disabled():
            return
        website = self.data_access.get_website()
        if not website:
            return
        shv_team_id = ShvApiClient.parse_team_id(website)
        if shv_team_id is None:
            # A website that isn't a matchcenter URL might be a typo (fixable) or another
            # portal (then the maintainer disables the sync via the button).
            await self.telegram_service.send_maintainer_message(
                f'SHV sync: the website of team {current_team_id()} is not a handball.ch '
                f'matchcenter team URL, cannot derive a team id.\n'
                f'website: {website}\n'
                f'expected shape: https://www.handball.ch/de/matchcenter/teams/<id>\n'
                f'Fix the website, or disable the sync for this team:',
                reply_markup=SyncMenu.build_maintainer_disable_markup(current_team_id()))
            return

        try:
            upcoming = await self._fetch_upcoming(shv_team_id)
        except (httpx.HTTPError, ShvApiError) as e:
            await self.telegram_service.send_maintainer_message(
                f'SHV sync: fetching games for team {current_team_id()} failed.\n'
                f'website: {website}\n'
                f'tried: {ShvApiClient.SHV_API_URL} with teamId={shv_team_id}\n'
                f'error: {e!r}')
            return
        bot_games = self.data_access.get_ordered_games()
        if not upcoming:
            # An empty upcoming feed while the bot still has future games smells like a
            # stale website: the SHV mints a NEW team id every season, so last season's
            # URL answers with only played games. Never derive delete questions from it.
            if bot_games:
                await self.telegram_service.send_maintainer_message(
                    f'SHV sync: the feed for team {current_team_id()} has no upcoming games, '
                    f'but the bot does. The website probably points at last season\'s team '
                    f'page (the SHV mints a new team id every season) - update it, or '
                    f'disable the sync.\n'
                    f'website: {website}\n'
                    f'tried: {ShvApiClient.SHV_API_URL} with teamId={shv_team_id}',
                    reply_markup=SyncMenu.build_maintainer_disable_markup(current_team_id()))
            return
        decisions = self.data_access.get_shv_sync_decisions()

        sync_plan = GameSyncPlanner.plan(upcoming, bot_games,
                                         _declined_adopt_pairs(decisions),
                                         _kept_manual_doc_ids(decisions))

        report_lines = [await self._apply_update(game_update)
                        for game_update in sync_plan.auto_updates]
        if report_lines:
            await self._send_to_admins('\n\n'.join([t(REPORT_HEADER)] + report_lines))

        decisions = self._drop_stale_decisions(decisions, upcoming, bot_games)
        await self._ask_questions(sync_plan, decisions, bot_games)

    async def _fetch_upcoming(self, shv_team_id: int) -> list[ShvGame]:
        shv_games = await ShvApiClient.fetch_games(shv_team_id)
        now = DateTimeUtils.get_local_now()
        # Only upcoming games: the bot's schedule is forward-looking, and syncing
        # history would touch games whose attendance answers are already settled.
        return [game for game in shv_games if not game.is_played and game.timestamp > now]

    async def _apply_update(self, game_update: GameUpdate) -> str:
        old_game = Game(game_update.old_timestamp, game_update.old_location,
                        game_update.game.opponent)
        self.data_access.update(game_update.game)
        line = (t('Game changed:') + '\n' + PrintUtils.pretty_print_long(old_game)
                + '\n→ ' + PrintUtils.pretty_print_long(game_update.game))
        if AttendanceResetPolicy.requires_attendance_reset(game_update.old_timestamp,
                                                           game_update.game.timestamp):
            await self._reset_and_notify_players(old_game, game_update.game)
            line += '\n' + t('Moved by more than 2 hours - all attendance answers were '
                             'reset and players re-asked.')
        return line

    #############
    # QUESTIONS #
    #############

    async def _ask_questions(self, sync_plan: SyncPlan, decisions: list[ShvSyncDecision],
                             bot_games: list[Game]):
        questions = []  # (kind, shv_game_id, game_doc_id, text)
        if not bot_games and sync_plan.new_games:
            # Empty schedule: one bulk question instead of a wall of per-game ones.
            questions.append((ShvDecisionKind.BULK_IMPORT, None, None,
                              t('The SHV schedule has {count} upcoming games and the bot none yet '
                                '- should I import them all?', count=len(sync_plan.new_games))))
        else:
            for shv_game in sync_plan.new_games:
                questions.append((ShvDecisionKind.CREATE, shv_game.shv_game_id, None,
                                  t('New game on the SHV schedule - should I add it?')
                                  + '\n' + _shv_game_line(shv_game)))
        for adopt in sync_plan.adopt_questions:
            questions.append((ShvDecisionKind.ADOPT, adopt.shv_game.shv_game_id,
                              adopt.bot_game.doc_id,
                              t('Is this the same game? The opponents differ, but the date matches.')
                              + '\n' + t('In the bot:') + ' '
                              + PrintUtils.pretty_print_long(adopt.bot_game)
                              + '\n' + t('On the SHV schedule:') + ' '
                              + _shv_game_line(adopt.shv_game)))
        for game in sync_plan.vanished:
            questions.append((ShvDecisionKind.DELETE_VANISHED, game.shv_game_id, game.doc_id,
                              t('This game is no longer on the SHV schedule - should I delete it?')
                              + '\n' + PrintUtils.pretty_print_long(game)))
        for game in sync_plan.manual_leftovers:
            questions.append((ShvDecisionKind.DELETE_MANUAL, None, game.doc_id,
                              t('This game is not on the SHV schedule - should I delete it? '
                                'If it should stay (e.g. a friendly game), answer No and I will '
                                'keep it without asking again.')
                              + '\n' + PrintUtils.pretty_print_long(game)))

        now = DateTimeUtils.get_local_now()
        for kind, shv_game_id, game_doc_id, text in questions:
            decision = _find_decision(decisions, kind, shv_game_id, game_doc_id)
            if decision is not None:
                if decision.status == ShvDecisionStatus.DECLINED and kind in (
                        ShvDecisionKind.ADOPT, ShvDecisionKind.DELETE_MANUAL):
                    continue  # final answers (also excluded from the plan - belt and braces)
                if decision.asked_at is not None and now - decision.asked_at < REASK_AFTER:
                    continue
                decision.status = ShvDecisionStatus.PENDING
                decision.asked_at = now
                self.data_access.update(decision)
            else:
                decision = self.data_access.add(ShvSyncDecision(
                    secrets.token_urlsafe(8), kind, ShvDecisionStatus.PENDING,
                    shv_game_id, game_doc_id, asked_at=now))
            await self._send_to_admins(text, SyncMenu.build_question_markup(decision.token))

    def _drop_stale_decisions(self, decisions: list[ShvSyncDecision], upcoming: list[ShvGame],
                              bot_games: list[Game]) -> list[ShvSyncDecision]:
        """Forget decisions whose subject is gone (game deleted, past, back on the feed,
        already linked) - a press on their leftover buttons then answers 'already
        handled'. Final answers survive as long as their game does."""
        feed_ids = {game.shv_game_id for game in upcoming}
        linked_ids = {game.shv_game_id for game in bot_games if game.shv_game_id is not None}
        games_by_doc_id = {game.doc_id: game for game in bot_games}
        kept = []
        for decision in decisions:
            if _is_stale(decision, feed_ids, linked_ids, games_by_doc_id, bool(bot_games)):
                self.data_access.delete_shv_sync_decision(decision)
            else:
                kept.append(decision)
        return kept

    ###########
    # ANSWERS #
    ###########

    async def approve(self, decision: ShvSyncDecision) -> str:
        """Execute a yes answer; returns the text the question message becomes."""
        match decision.kind:
            case ShvDecisionKind.CREATE:
                return await self._approve_create(decision)
            case ShvDecisionKind.ADOPT:
                return await self._approve_adopt(decision)
            case ShvDecisionKind.DELETE_VANISHED | ShvDecisionKind.DELETE_MANUAL:
                return await self._approve_delete(decision)
            case ShvDecisionKind.BULK_IMPORT:
                return await self._approve_bulk_import(decision)
            case _:
                raise ValueError(f'Unhandled decision kind: {decision.kind}')

    async def _approve_create(self, decision: ShvSyncDecision) -> str:
        shv_game = await self._find_in_feed(decision.shv_game_id)
        if shv_game is None:
            self.data_access.delete_shv_sync_decision(decision)
            return t('This game has left the SHV schedule in the meantime - nothing imported.')
        game = self.data_access.add(Game(shv_game.timestamp, shv_game.location,
                                         shv_game.opponent, shv_game.shv_game_id))
        await self._notify_players_new_game(game)
        self.data_access.delete_shv_sync_decision(decision)
        return t('Game added 👍 - players were notified.')

    async def _approve_adopt(self, decision: ShvSyncDecision) -> str:
        shv_game = await self._find_in_feed(decision.shv_game_id)
        try:
            bot_game = self.data_access.get_game(decision.game_doc_id)
        except ObjectNotFoundException:
            bot_game = None
        if shv_game is None or bot_game is None:
            self.data_access.delete_shv_sync_decision(decision)
            return t('This question is outdated - the game changed in the meantime.')
        updated = GameSyncPlanner.apply_shv_data(bot_game, shv_game)
        self.data_access.update(updated)
        if AttendanceResetPolicy.requires_attendance_reset(bot_game.timestamp, updated.timestamp):
            await self._reset_and_notify_players(bot_game, updated)
        self.data_access.delete_shv_sync_decision(decision)
        return t('Linked 👍 - the game now mirrors the SHV schedule.')

    async def _approve_delete(self, decision: ShvSyncDecision) -> str:
        self.data_access.delete_event(Event.GAME, decision.game_doc_id)
        self.data_access.delete_shv_sync_decision(decision)
        return t('Game deleted.')

    async def _approve_bulk_import(self, decision: ShvSyncDecision) -> str:
        shv_team_id = self._current_shv_team_id()
        if shv_team_id is None:
            self.data_access.delete_shv_sync_decision(decision)
            return t('This question is outdated - the game changed in the meantime.')
        # Freshly fetched and re-planned: the feed may have moved since the question.
        upcoming = await self._fetch_upcoming(shv_team_id)
        sync_plan = GameSyncPlanner.plan(upcoming, self.data_access.get_ordered_games())
        created = [self.data_access.add(Game(shv_game.timestamp, shv_game.location,
                                             shv_game.opponent, shv_game.shv_game_id))
                   for shv_game in sync_plan.new_games]
        await self._notify_players_bulk(created)
        self.data_access.delete_shv_sync_decision(decision)
        return t('Imported {count} games 👍 - players were notified.', count=len(created))

    def decline(self, decision: ShvSyncDecision):
        decision.status = ShvDecisionStatus.DECLINED
        decision.asked_at = DateTimeUtils.get_local_now()
        self.data_access.update(decision)

    def record_decline_reason(self, decision: ShvSyncDecision, reason: str):
        decision.reason = reason
        self.data_access.update(decision)

    async def report_decline_to_maintainer(self, decision: ShvSyncDecision, admin_name: str):
        await self.telegram_service.send_maintainer_message(
            f'SHV sync: {admin_name} declined {decision.kind.name} - {self.describe(decision)}')

    async def report_decline_reason_to_maintainer(self, decision: ShvSyncDecision):
        await self.telegram_service.send_maintainer_message(
            f'SHV sync: reason for the declined {decision.kind.name} - {self.describe(decision)}')

    def describe(self, decision: ShvSyncDecision) -> str:
        """Everything the maintainer needs to judge a declined question (plain English -
        maintainer diagnostics are not localized)."""
        parts = [f'shv_game_id={decision.shv_game_id}', f'game_doc_id={decision.game_doc_id}']
        if decision.game_doc_id is not None:
            try:
                parts.append(repr(self.data_access.get_game(decision.game_doc_id)))
            except ObjectNotFoundException:
                parts.append('(game no longer in the database)')
        if decision.reason is not None:
            parts.append(f'reason: {decision.reason}')
        return ', '.join(parts)

    async def _find_in_feed(self, shv_game_id: int) -> ShvGame | None:
        shv_team_id = self._current_shv_team_id()
        if shv_team_id is None:
            return None
        upcoming = await self._fetch_upcoming(shv_team_id)
        return next((game for game in upcoming if game.shv_game_id == shv_game_id), None)

    def _current_shv_team_id(self) -> int | None:
        website = self.data_access.get_website()
        return ShvApiClient.parse_team_id(website) if website else None

    def disable_for_team(self, team_id: str):
        """The maintainer-button action: stop syncing this team (its portal is not
        readable). Runs OUTSIDE the team's ambient context, hence the explicit id."""
        with team_context(team_id):
            self.data_access.set_shv_sync_disabled(True)

    #############
    # MESSAGING #
    #############

    async def _send_to_admins(self, message: str, reply_markup=None):
        # Sync questions and reports go to the admins' DMs (never the group chat: the
        # buttons are admin decisions). Composed once in the team language, like the
        # trainer summaries.
        for user_to_state in self.data_access.get_admins_to_state():
            user = self.data_access.get_user_by_doc_id(user_to_state.user_id)
            await self.telegram_service.send_message(update=user, all_buttons=None,
                                                     message=message, reply_markup=reply_markup)

    async def _reset_and_notify_players(self, old_game: Game, updated_game: Game):
        self.data_access.reset_all_player_event_attendance(Event.GAME, updated_game.doc_id)
        await PlayerNotifications.push_event_to_players(
            self.telegram_service, self.data_access, self.data_access.get_all_players(),
            updated_game, Event.GAME, intro_message_type=MessageType.EVENT_TIMESTAMP_CHANGED,
            intro_extra_text=PrintUtils.pretty_print_event_datetime(old_game))

    async def _notify_players_new_game(self, game: Game):
        await PlayerNotifications.push_event_to_players(
            self.telegram_service, self.data_access, self.data_access.get_all_players(),
            game, Event.GAME, intro_message_type=MessageType.EVENT_ADDED)

    async def _notify_players_bulk(self, created: list[Game]):
        # One intro plus one attendance card per game - the per-game EVENT_ADDED intro
        # would double the message count on a whole-season import.
        for player in self.data_access.get_all_players():
            with recipient_language_context(self.data_access, player.telegramId):
                await self.telegram_service.send_message(
                    update=player, all_buttons=None,
                    message=t('I imported the upcoming games from the SHV schedule - '
                              'please answer for each:'))
                for game in created:
                    message_text = (PrintUtils.event_label(Event.GAME) + ' | '
                                    + PrintUtils.pretty_print(game, AttendanceState.UNSURE))
                    await self.telegram_service.send_message(
                        update=player, all_buttons=None, message=message_text,
                        reply_markup=EventsMenu.build_attendance_markup(Event.GAME, game.doc_id))


def _declined_adopt_pairs(decisions: list[ShvSyncDecision]) -> set[tuple[int, str]]:
    return {(decision.shv_game_id, decision.game_doc_id) for decision in decisions
            if decision.kind == ShvDecisionKind.ADOPT
            and decision.status == ShvDecisionStatus.DECLINED}


def _kept_manual_doc_ids(decisions: list[ShvSyncDecision]) -> set[str]:
    return {decision.game_doc_id for decision in decisions
            if decision.kind == ShvDecisionKind.DELETE_MANUAL
            and decision.status == ShvDecisionStatus.DECLINED}


def _find_decision(decisions: list[ShvSyncDecision], kind: ShvDecisionKind,
                   shv_game_id: int | None, game_doc_id: str | None) -> ShvSyncDecision | None:
    return next((decision for decision in decisions
                 if decision.kind == kind and decision.shv_game_id == shv_game_id
                 and decision.game_doc_id == game_doc_id), None)


def _is_stale(decision: ShvSyncDecision, feed_ids: set, linked_ids: set,
              games_by_doc_id: dict, any_bot_games: bool) -> bool:
    match decision.kind:
        case ShvDecisionKind.CREATE:
            return decision.shv_game_id not in feed_ids or decision.shv_game_id in linked_ids
        case ShvDecisionKind.ADOPT:
            bot_game = games_by_doc_id.get(decision.game_doc_id)
            return (decision.shv_game_id not in feed_ids or bot_game is None
                    or bot_game.shv_game_id is not None)
        case ShvDecisionKind.DELETE_VANISHED:
            return (decision.game_doc_id not in games_by_doc_id
                    or decision.shv_game_id in feed_ids)
        case ShvDecisionKind.DELETE_MANUAL:
            return decision.game_doc_id not in games_by_doc_id
        case ShvDecisionKind.BULK_IMPORT:
            return any_bot_games
        case _:
            return True


def _shv_game_line(shv_game: ShvGame) -> str:
    return PrintUtils.pretty_print_long(
        Game(shv_game.timestamp, shv_game.location, shv_game.opponent))
