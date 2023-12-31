from functools import partial
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
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Utils.CommandDescriptions import CommandDescriptions
from Utils import PrintUtils

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
                all_buttons=self.get_commands_for_buttons(user_to_state.role, UserState.DEFAULT,
                                                          update.effective_chat.id),
                message_type=MessageType.ERROR,
                message_extra_text=str(e))
            await self.telegram_service.send_maintainer_message('Error caught in Node.handle()', update, e)

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

    def add_event_transition(self, command: str, action: Callable = None, allowed_roles: RoleSet = RoleSet.EVERYONE,
                             new_state: UserState = None, needs_description: bool = True, document_id: str = None,
                             event_type: Event = None, additional_data_func: Callable = None,
                             is_active_function: partial = None) -> Transition:
        new_transition = EventTransition(command, action, document_id, event_type, allowed_roles,
                                         new_state=new_state, needs_description=needs_description,
                                         additional_data_func=additional_data_func,
                                         is_active_function=is_active_function)
        self.transitions.append(new_transition)
        return new_transition

    def add_transition(self, command: str, action: Callable = None, allowed_roles: RoleSet = RoleSet.EVERYONE,
                       new_state: UserState = None, needs_description: bool = True, is_active_function: Callable = None,
                       message_type: MessageType = None) -> Transition:
        if action is None:
            action = partial(self.handle_default, message_type=message_type)
            # TODO Add defaultNode-transition to adminNode
            # refactor - use message_type

        new_transition = Transition(command, action, allowed_roles, new_state=new_state,
                                    needs_description=needs_description, is_active_function=is_active_function)
        self.transitions.append(new_transition)
        return new_transition

    def add_continue_later(self) -> None:
        self.add_transition('continue later', self.handle_continue_later, new_state=UserState.DEFAULT)

    def clear_event_transitions(self):
        self.transitions = [transition for transition in self.transitions if type(transition) is not EventTransition]

    ####################
    # DEFAULT HANDLERS #
    ####################

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        commands_for_buttons = self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id)
        commands_for_text = self.get_commands_for_help(user_to_state.role, new_state)
        message = CommandDescriptions.get_descriptions(commands_for_text)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=commands_for_buttons,
            message=message)

    async def handle_continue_later(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, UserState.DEFAULT, update.effective_chat.id),
            message_type=MessageType.CONTINUE_LATER)

    async def handle_default(self, update: Update, user_to_state: UsersToState, new_state: UserState,
                             message_type: MessageType):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=message_type)

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

    def get_commands_for_buttons(self, role: Role, new_state: UserState, telegram_id: int) -> [str]:
        if new_state is None:
            new_node = self
        else:
            new_node = self.nodes[new_state]

        all_commands = list(
            filter(lambda t:
                   t.is_for_role(role) and t.is_active(),
                   new_node.transitions))

        event_transitions = [x for x in all_commands if isinstance(x, EventTransition)]
        if len(event_transitions) > 0:
            telegram_user = self.data_access.get_user(telegram_id)
            all_attendances = self.data_access.get_all_event_attendances(telegram_user)

        result = []
        for command in all_commands:
            button_description = command.command
            if isinstance(command, EventTransition) and command.additional_data_func and role is not Role.SPECTATOR:
                button_description = button_description.title()
                data = command.additional_data_func()
                attendance = all_attendances.get(command.document_id)
                pretty_print = PrintUtils.pretty_print_event_stats(data, command.event_type, attendance)
                button_description += f" | {pretty_print}"
            result.append(button_description)

        return result
