from functools import partial
from abc import ABC
from telegram import Update
from typing import Callable

from framework.Services.TelegramService import TelegramService
from framework.Services.UserStateService import UserStateService

from data.DataAccess import DataAccess

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.RoleSet import RoleSet
from Enums.Role import Role

from domain.entities.UsersToState import UsersToState

from framework.CommandDescriptions import CommandDescriptions

from framework.Transitions.Transition import Transition


class Node(ABC):

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess):
        self.state = state
        self.data_access = data_access
        self.user_state_service = user_state_service
        self.telegram_service = telegram_service
        self.transitions = list()
        # Where free text that matches no transition lands: menu screens show help,
        # typed-input screens (wizard, field edit, URL) consume it as the expected value.
        self.fallback_action = self.handle_help
        # Set via enable_main_menu_escapes: lets any main-menu command break out of a
        # typed-input node instead of being swallowed as input.
        self.main_menu_escape_cleanup = None
        self.add_transition('help', self.handle_help, allowed_roles=RoleSet.EVERYONE)
        self.add_transition('/help', self.handle_help, allowed_roles=RoleSet.EVERYONE,
                            needs_description=False, in_keyboard=False)
        self.nodes = dict()

    def add_nodes(self, nodes: dict):
        self.nodes = nodes

    async def handle(self, update: Update, user_to_state: UsersToState) -> None:
        try:
            command = update.message.text.lower()
            transition = self.get_transition(command, user_to_state.role)
            if transition is None:
                await self.fallback_action(update, user_to_state, None)
                return
            action = transition.action
            new_state = transition.new_state
            await action(update, user_to_state, new_state)

            if not transition.update_state:
                return
            self.user_state_service.update_user_state(user_to_state, new_state)

        except Exception as e:
            # The user always gets the generic ERROR text; report_exception decides whether the
            # maintainer is alerted (unexpected) or the miss is only logged (expected).
            await self.telegram_service.send_message(
                update=update,
                all_buttons=self.get_commands_for_buttons(user_to_state.role, UserState.DEFAULT),
                message_type=MessageType.ERROR)
            await self.telegram_service.report_exception('Exception in Node.handle', e, update)

    ###############
    # TRANSITIONS #
    ###############

    def get_transition(self, command: str, role: Role) -> Transition | None:
        """The matching transition, a main-menu escape if the node allows one, or None
        (the caller runs fallback_action)."""
        transitions = list(filter(lambda t: t.can_be_taken(command, role), self.transitions))
        if len(transitions) > 0:
            return transitions[0]
        if self.main_menu_escape_cleanup is not None and self._is_main_menu_command(command, role):
            return Transition(command, self._handle_main_menu_escape, needs_description=False, in_keyboard=False)
        return None

    def add_transition(self, command: str, action: Callable = None, allowed_roles: RoleSet = RoleSet.EVERYONE,
                       new_state: UserState = None, needs_description: bool = True, is_active_function: Callable = None,
                       message_type: MessageType = None, in_keyboard: bool = True) -> Transition:
        if action is None:
            action = partial(self.handle_default, message_type=message_type)

        new_transition = Transition(command, action, allowed_roles, new_state=new_state,
                                    needs_description=needs_description, is_active_function=is_active_function,
                                    in_keyboard=in_keyboard)
        self.transitions.append(new_transition)
        return new_transition

    def enable_main_menu_escapes(self, cleanup: Callable[[UsersToState], None]) -> None:
        """Let every main-menu command break out of this node: run the node's cleanup
        (drop a draft, clear staged input), then dispatch the command as if the user
        were already back on the main menu. Which commands escape is derived from the
        DEFAULT node's transitions, so new main-menu entries can't go stale here."""
        self.main_menu_escape_cleanup = cleanup

    def _is_main_menu_command(self, command: str, role: Role) -> bool:
        return any(t.can_be_taken(command, role) for t in self.nodes[UserState.DEFAULT].transitions)

    async def _handle_main_menu_escape(self, update: Update, user_to_state: UsersToState,
                                       new_state: UserState) -> None:
        self.main_menu_escape_cleanup(user_to_state)
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self.nodes[UserState.DEFAULT].handle(update, user_to_state)

    ####################
    # DEFAULT HANDLERS #
    ####################

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        # Help text lists THIS screen's commands; the reply keyboard is always the
        # static main-menu one, so asking for help mid-flow can't swap it out.
        commands_for_buttons = self.get_commands_for_buttons(user_to_state.role, UserState.DEFAULT)
        commands_for_text = self.get_commands_for_help(user_to_state.role, new_state)
        message = CommandDescriptions.get_descriptions(commands_for_text)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=commands_for_buttons,
            message=message)

    async def handle_default(self, update: Update, user_to_state: UsersToState, new_state: UserState,
                             message_type: MessageType):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=message_type)

    #############
    # UTILITIES #
    #############

    def get_active_transitions(self, role: Role, new_state: UserState) -> [Transition]:
        if new_state is None:
            new_node = self
        else:
            new_node = self.nodes[new_state]

        return [t for t in new_node.transitions if t.is_for_role(role) and t.is_active()]

    def get_commands_for_help(self, role: Role, new_state: UserState) -> [str]:
        return [t.command for t in self.get_active_transitions(role, new_state) if t.needs_description]

    def get_commands_for_buttons(self, role: Role, new_state: UserState) -> [str]:
        return [t.command for t in self.get_active_transitions(role, new_state) if t.in_keyboard]
