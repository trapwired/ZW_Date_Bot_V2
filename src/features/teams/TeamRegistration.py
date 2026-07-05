from telegram import Update, ChatMemberAdministrator, ChatMemberOwner
from telegram.constants import ChatMemberStatus, ChatType
from telegram.error import TelegramError

from Enums.Role import Role
from Enums.Table import Table
from Enums.UserState import UserState

from data.TenantContext import team_context

from domain.entities.Team import Team
from domain.entities.TelegramUser import TelegramUser

from features.onboarding import WelcomeGuide

from framework.Services.TeamService import TeamService
from framework.Services.TelegramService import TelegramService
from framework.Services.UserStateService import UserStateService

from Utils import Format
from Utils.CustomExceptions import GroupChatAlreadyRegisteredException, ObjectNotFoundException

COMMAND = '/register_team'

USAGE_TEXT = ('To register this group as a team, send:\n'
              '/register_team followed by your team name')

def _is_in_group(chat_member) -> bool:
    """RESTRICTED alone is ambiguous: Telegram keeps the status for former members
    whose restrictions outlive the membership - is_member disambiguates."""
    if chat_member.status == ChatMemberStatus.RESTRICTED:
        return chat_member.is_member
    return chat_member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR)


def is_register_team_command(update: Update) -> bool:
    if not update.message or not update.message.text:
        return False
    tokens = update.message.text.split()
    if not tokens:  # whitespace-only messages are truthy but have no tokens
        return False
    # In groups Telegram may address commands explicitly: /register_team@BotName
    return tokens[0].split('@')[0] == COMMAND


class TeamRegistration:
    """Handles /register_team inside a group chat: creates the team bound to that group
    (the group IS the team's identity anchor) and makes the issuer its first admin.
    This is the only group message the bot acts on - everything else in groups stays
    ignored."""

    def __init__(self, bot, telegram_service: TelegramService, user_state_service: UserStateService,
                 team_service: TeamService, data_access, node_handler):
        self.bot = bot
        self.telegram_service = telegram_service
        self.user_state_service = user_state_service
        self.team_service = team_service
        self.data_access = data_access
        # For the reply keyboard of the setup DM; nodes exist by the time updates arrive.
        self.node_handler = node_handler

    async def handle(self, update: Update) -> None:
        group_chat_id = update.effective_chat.id
        issuer = update.effective_user

        parts = update.message.text.split(maxsplit=1)
        team_name = parts[1].strip() if len(parts) > 1 else ''
        if not team_name:
            await self._reply(update, USAGE_TEXT)
            return

        if not await self._issuer_may_register(group_chat_id, issuer.id):
            # Any group member can see the command; only those Telegram itself trusts
            # with the group (owner/admin) may claim it as a team.
            await self._reply(update, 'Only an admin or the owner of this group can register it as a team.')
            return

        issuer_state = self._lookup_user_state(issuer.id)
        if issuer_state is not None and issuer_state.team_id:
            # One user, one team (ADR 0001) - and the first admin must belong to the
            # team they just created.
            await self._reply(update, 'You already belong to a team, so you cannot register another one.')
            return

        try:
            self._register_and_stamp_admin(team_name, group_chat_id, issuer, issuer_state)
        except GroupChatAlreadyRegisteredException:
            await self._reply(update, 'This group already has a registered team.')
            return

        issuer_name = Format.escape(issuer.first_name)
        await self._reply(
            update,
            f'✅ Team "{Format.escape(team_name)}" is registered, and {issuer_name} is its first admin!\n\n'
            f'Everyone in this group: open a private chat with me and send /start to join. '
            f'{issuer_name} can manage events, roles and more via the admin menu there.')

    def _register_and_stamp_admin(self, team_name: str, group_chat_id: int, issuer, issuer_state) -> Team:
        team = self.team_service.register_team(team_name, group_chat_id)
        if issuer_state is None:
            issuer_state = self.user_state_service.register_user(
                TelegramUser(issuer.id, issuer.first_name, issuer.last_name))
        self.user_state_service.join_team(issuer_state, team.doc_id, Role.ADMIN)
        return team

    ####################
    # GROUP MEMBERSHIP #
    ####################

    async def handle_my_chat_member(self, update: Update) -> None:
        """The bot's own membership in a chat changed. Being ADDED to a group by a group
        admin registers that group as a team (the guided-onboarding trigger); being
        REMOVED from a fresh team's group rolls the setup back."""
        if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return  # private-chat block/unblock events carry no team meaning
        change = update.my_chat_member
        was_in = _is_in_group(change.old_chat_member)
        is_in = _is_in_group(change.new_chat_member)
        if not was_in and is_in:
            await self._handle_added_to_group(update)
        elif was_in and not is_in:
            await self._handle_removed_from_group(update)

    async def _handle_added_to_group(self, update: Update) -> None:
        group_chat_id = update.effective_chat.id
        adder = update.my_chat_member.from_user

        existing = self.team_service.find_team_by_group_chat(group_chat_id)
        if existing is not None:
            await self._reply(update, f'Good to be back! This group is already the team '
                                      f'"{Format.escape(existing.name)}" - members can open a private '
                                      'chat with me and send /start to join.')
            return
        if not await self._issuer_may_register(group_chat_id, adder.id):
            await self._reply(update, 'Thanks for adding me! A group admin or the owner can set this '
                                      f'group up as a team: remove and re-add me, or use the command.\n{USAGE_TEXT}')
            return
        adder_state = self._lookup_user_state(adder.id)
        if adder_state is not None and adder_state.team_id:
            await self._reply(update, f'{Format.escape(adder.first_name)} already belongs to a team, so they '
                                      'cannot register another one - a different group admin can remove and '
                                      f're-add me, or use the command.\n{USAGE_TEXT}')
            return

        team_name = (update.effective_chat.title or '').strip() or f'Team {group_chat_id}'
        team = self._register_and_stamp_admin(team_name, group_chat_id, adder, adder_state)
        await self._send_setup_guide(update, team, adder)

    async def _send_setup_guide(self, update: Update, team: Team, adder) -> None:
        guide = WelcomeGuide.build_admin_setup_guide(team.name)
        buttons = self.node_handler.get_node(UserState.DEFAULT).get_commands_for_buttons(
            Role.ADMIN, UserState.DEFAULT)
        try:
            await self.telegram_service.send_onboarding_message(adder.id, guide, buttons)
        except TelegramError:
            # Telegram forbids messaging a user who never opened a chat with the bot.
            username = await self.telegram_service.get_bot_username()
            await self._reply(update, f'🎉 Team "{Format.escape(team.name)}" is registered! '
                                      f'{Format.escape(adder.first_name)}, I cannot message you first - '
                                      f'open https://t.me/{username} and press Start to finish the setup.')
            return
        await self._reply(update, f'🎉 This group is now the team "{Format.escape(team.name)}"! Everyone: '
                                  'open a private chat with me and send /start to join. '
                                  f'{Format.escape(adder.first_name)}, I sent you the setup steps.')

    async def _handle_removed_from_group(self, update: Update) -> None:
        team = self.team_service.find_team_by_group_chat(update.effective_chat.id)
        if team is None:
            return
        members = self.data_access.get_users_to_state_by_team(team.doc_id)
        if self._team_saw_use(team, members):
            # Established team: never auto-delete data (ADR 0001 - manual cleanup).
            await self.telegram_service.send_maintainer_message(
                f'Bot was removed from the group of team "{team.name}" ({team.doc_id}). '
                'Data kept - clean up manually if the team is really gone.')
            return

        self.team_service.delete_team(team)
        for member in members:
            self.user_state_service.leave_team(member)
        await self.telegram_service.send_maintainer_message(
            f'Setup of team "{team.name}" was cancelled (bot removed from its group); '
            'the team was rolled back.')
        for member in members:
            try:
                user = self.data_access.get_user_by_doc_id(member.user_id)
                await self.telegram_service.send_onboarding_message(
                    user.telegramId, f'Setup cancelled - the team "{Format.escape(team.name)}" was rolled '
                                     'back. Add me to a group chat again anytime to start over.')
            except (TelegramError, ObjectNotFoundException):
                pass  # best-effort: rollback already happened, the next member still gets told

    def _team_saw_use(self, team: Team, members: list) -> bool:
        """Fresh = still deletable: nobody but the registering admin joined and no
        event (past or future) was ever created."""
        if len(members) > 1:
            return True
        with team_context(team.doc_id):
            return any(self.data_access.has_any_docs(table)
                       for table in (Table.GAMES_TABLE, Table.TRAININGS_TABLE, Table.TIMEKEEPING_TABLE))

    async def _issuer_may_register(self, group_chat_id: int, issuer_id: int) -> bool:
        if int(issuer_id) == int(self.telegram_service.maintainer_chat_id):
            return True
        try:
            member = await self.bot.get_chat_member(group_chat_id, issuer_id)
        except TelegramError:
            # Can't verify -> don't register. The issuer can simply retry.
            return False
        return isinstance(member, (ChatMemberOwner, ChatMemberAdministrator))

    def _lookup_user_state(self, telegram_id: int):
        try:
            return self.user_state_service.get_user_state(telegram_id)
        except ObjectNotFoundException:
            return None

    async def _reply(self, update: Update, message: str) -> None:
        # update.effective_chat is the group, so this replies where the command was sent.
        await self.telegram_service.send_message(update=update, all_buttons=None, message=message)
