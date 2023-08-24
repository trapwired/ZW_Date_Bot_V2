import sys
import traceback
from abc import ABC
from telegram import Update
from typing import Callable

from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService

from Data.DataAccess import DataAccess

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.RoleSet import RoleSet
from Enums.Role import Role

from databaseEntities.UsersToState import UsersToState

from Utils.CommandDescriptions import CommandDescriptions

from Transitions.Transition import Transition
from Transitions.EventTransition import EventTransition


class Node(ABC):

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess):
        self.state = state
        self.data_access = data_access
        self.user_state_service = user_state_service
        self.telegram_service = telegram_service
        self.transitions = list()
        self.help_transition = self.add_transition('/help', self.handle_help, allowed_roles=RoleSet.EVERYONE)
        self.nodes = dict()

    def add_nodes(self, nodes: dict):
        self.nodes = nodes

    async def handle(self, update: Update, user_to_state: UsersToState) -> None:
        try:
            command = update.message.text.lower()
            transition = self.get_transition(command, user_to_state.role)
            action = transition.action
            new_state = transition.new_state
            await action(update, user_to_state, new_state)

            if not transition.update_state:
                return
            self.user_state_service.update_user_state(user_to_state, new_state)

        except Exception as e:
            await self.telegram_service.send_message(
                update=update,
                all_buttons=self.get_commands_for_buttons(user_to_state.role, UserState.DEFAULT),
                message_type=MessageType.ERROR,
                message_extra_text=str(e))
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
                       new_state: UserState = None, needs_description: bool = True,
                       document_id: str = None, is_active_function: Callable = None) -> Transition:
        if document_id is not None:
            new_transition = EventTransition(command, action, document_id, allowed_roles, new_state=new_state,
                                             needs_description=needs_description)
        else:
            new_transition = Transition(command, action, allowed_roles, new_state=new_state,
                                        needs_description=needs_description, is_active_function=is_active_function)
        self.transitions.append(new_transition)
        return new_transition

    def add_continue_later(self) -> None:
        self.add_transition('continue later', self.handle_continue_later, new_state=UserState.DEFAULT)

    ####################
    # DEFAULT HANDLERS #
    ####################

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        commands_for_buttons = self.get_commands_for_buttons(user_to_state.role, new_state)
        commands_for_text = self.get_commands_for_help(user_to_state.role, new_state)
        message = CommandDescriptions.get_descriptions(commands_for_text)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=commands_for_buttons,
            message=message)

    async def handle_continue_later(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, UserState.DEFAULT),
            message_type=MessageType.CONTINUE_LATER)

    #############
    # UTILITIES #
    #############

    def get_commands_for_help(self, role: Role, new_state: UserState) -> [str]:
        if new_state is None:
            new_node = self
        else:
            new_node = self.nodes[new_state]

        all_commands = list(
            filter(lambda t:
                   t.is_for_role(role) and t.needs_description,
                   new_node.transitions))
        return [x.command for x in all_commands]

    def get_commands_for_buttons(self, role: Role, new_state: UserState) -> [str]:
        if new_state is None:
            new_node = self
        else:
            new_node = self.nodes[new_state]

        all_commands = list(
            filter(lambda t:
                   t.is_for_role(role) and t.is_active(),
                   new_node.transitions))
        return [x.command for x in all_commands]
