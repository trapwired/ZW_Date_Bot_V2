import sys
import traceback
from abc import ABC
from telegram import Update
from typing import Callable

from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService

from Data.DataAccess import DataAccess
from Nodes.Transition import Transition

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.RoleSet import RoleSet

from databaseEntities.UsersToState import UsersToState

from src.Enums.Role import Role


class Node(ABC):

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess):
        self.state = state
        self.data_access = data_access
        self.user_state_service = user_state_service
        self.telegram_service = telegram_service
        self.transitions = list()
        self.help_transition = self.add_transition('/help', self.handle_help, allowed_roles=RoleSet.EVERYONE)

    async def handle(self, update: Update, users_to_state: UsersToState) -> None:
        try:
            command = update.message.text.lower()
            transition = self.get_transition(command, users_to_state.role)
            action = transition.action
            await action(update, users_to_state)

            if not transition.update_state:
                return
            self.user_state_service.update_user_state(users_to_state, transition.new_state)

        except Exception as e:
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.ERROR, str(e))
            traceback.print_exception(*sys.exc_info())

    ###############
    # TRANSITIONS #
    ###############

    def get_transition(self, command: str, role: Role) -> Transition:
        transitions = list(filter(lambda t: t.can_be_taken(command, role), self.transitions))
        if len(transitions) == 0:
            transition = self.help_transition
        else:
            transition = transitions[0]
        return transition

    def add_transition(self, command: str, action: Callable, allowed_roles: RoleSet = RoleSet.EVERYONE,
                       new_state: UserState = None) -> Transition:
        new_transition = Transition(command, action, allowed_roles, new_state=new_state)
        self.transitions.append(new_transition)
        return new_transition

    def add_continue_later(self) -> None:
        self.add_transition('continue later', self.handle_continue_later, new_state=UserState.DEFAULT)

    ####################
    # DEFAULT HANDLERS #
    ####################

    async def handle_help(self, update: Update, user_to_state: UsersToState) -> None:
        await self.telegram_service.send_message(
            update.effective_chat.id,
            MessageType.HELP,
            extra_text=str(type(self)),
            keyboard_btn_list=self.generate_keyboard(user_to_state.role))

    async def handle_continue_later(self, update: Update, user_to_state: UsersToState) -> None:
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.CONTINUE_LATER,
                                                 update.effective_user.first_name)

    #############
    # UTILITIES #
    #############

    def generate_keyboard(self, role: Role) -> [[str]]:
        all_commands = list(filter(lambda t: t.is_for_role(role), self.transitions))
        return [[x.command] for x in all_commands]
