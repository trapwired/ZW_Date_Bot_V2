
import logging

import telegram
from telegram import Update, ChatMemberRestricted, ChatMemberMember, ChatMemberAdministrator, ChatMemberOwner
from telegram.error import TelegramError

from framework.Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.Role import Role
from Enums.UserState import UserState

from data.DataAccess import DataAccess

from framework.Services.UserStateService import UserStateService
from framework.Services.TelegramService import TelegramService
from framework.Services.TeamService import TeamService

from domain.entities.Team import Team
from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState

from features.onboarding import OnboardingMenu
from features.onboarding import WelcomeGuide

from Utils.CustomExceptions import ObjectNotFoundException


def create_user(update: Update) -> TelegramUser:
    return TelegramUser(update.effective_chat.id, update.effective_user.first_name, update.effective_user.last_name)


class InitNode(Node):

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, bot: telegram.Bot, team_service: TeamService):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.bot = bot
        self.team_service = team_service

    async def handle(self, update: Update, user_to_state: UsersToState):
        telegram_id = update.effective_chat.id
        try:
            users_to_state = self.user_state_service.get_user_state(telegram_id)
        except ObjectNotFoundException:
            user = create_user(update)
            users_to_state = self.user_state_service.register_user(user)
        await super().handle(update, users_to_state)

    async def handle_start(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        telegram_id = update.effective_chat.id
        team = await self.find_membership_team(telegram_id)
        if team is not None:
            # A re-/starting admin (e.g. state healed back to INIT) must not be
            # demoted - everyone else joins as PLAYER.
            role = Role.ADMIN if user_to_state.role is Role.ADMIN else Role.PLAYER
            self.user_state_service.join_team(user_to_state, team.doc_id, role)
            await self.telegram_service.send_message(
                update=update,
                all_buttons=self.get_commands_for_buttons(user_to_state.role, UserState.DEFAULT),
                message_type=MessageType.WELCOME,
                message_extra_text=team.name)
            await self.telegram_service.send_message(
                update=update,
                all_buttons=None,
                message=WelcomeGuide.build_guide(user_to_state.role, team.name))
        else:
            new_state = UserState.REJECTED
            user_to_state = user_to_state.add_role(Role.REJECTED)
            self.user_state_service.update_user_state(user_to_state, new_state)
            await self.telegram_service.send_message(
                update=update,
                all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
                message_type=MessageType.REJECTED,
                reply_markup=OnboardingMenu.build_choice_markup())

    async def find_membership_team(self, telegram_id) -> Team | None:
        """A team whose group chat the user is a member of. Iteration order is arbitrary
        (Firestore doc order) - belonging to several teams' groups is a non-goal per
        ADR 0001, whoever matches first wins. A team whose group the bot cannot query
        (kicked, bad id, transient API error) is skipped, not fatal."""
        teams = self.team_service.get_all_teams()
        if not teams:
            logging.warning('/start with no registered teams - every member is rejected')
        for team in teams:
            try:
                member = await self.bot.get_chat_member(team.group_chat_id, telegram_id)
            except TelegramError:
                continue
            if isinstance(member, (ChatMemberOwner, ChatMemberAdministrator, ChatMemberMember, ChatMemberRestricted)):
                return team
        return None

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.WRONG_START_COMMAND)
