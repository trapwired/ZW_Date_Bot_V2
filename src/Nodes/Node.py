from abc import ABC
from telegram import Update
from typing import Callable

from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService

from Data.DataAccess import DataAccess
from Nodes.Transition import Transition

from Enums.MessageType import MessageType
from Enums.UserState import UserState

from databaseEntities.UsersToState import UsersToState


class Node(ABC):

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess):
        self.state = state
        self.data_access = data_access
        self.user_state_service = user_state_service
        self.telegram_service = telegram_service
        self.transitions = dict()
        self.add_transition('/help', self.handle_help)

    async def handle(self, update: Update, users_to_state: UserStateService) -> None:
        try:
            command = update.message.text.lower()
            transition = self.get_transition(command)
            action = transition.action
            await action(update, users_to_state)

            if not transition.update_state:
                return
            self.user_state_service.update_user_state(users_to_state, transition.new_state)

        except Exception as e:
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.ERROR, str(e))

    ###############
    # TRANSITIONS #
    ###############

    def transitions(self) -> dict:
        return self.transitions

    def get_transition(self, command: str) -> Transition:
        transition = self.transitions.get(command)
        if transition is None:
            transition = self.transitions.get('/help')
        return transition

    def add_transition(self, command: str, action: Callable, new_state: UserState = None) -> None:
        """
        :param command: str => should be in the form of /someCommand
        :param action: Callable => the action to take during this transition, defined in the Nodeclass itself
        :param new_state: PlayerState => if it's none, update_state is set
        to False, which implies not changing the node during the transition
        """
        command = command.lower()
        if new_state is None:
            self.transitions[command] = Transition(action, new_state, update_state=False)
        else:
            self.transitions[command] = Transition(action, new_state, update_state=True)

    def add_continue_later(self) -> None:
        self.add_transition('continue later', self.handle_continue_later, UserState.DEFAULT)

    ####################
    # DEFAULT HANDLERS #
    ####################

    async def handle_help(self, update: Update, user_to_state: UsersToState) -> None:
        await self.telegram_service.send_message(
            update.effective_chat.id,
            MessageType.HELP,
            extra_text=str(type(self)),
            keyboard_btn_list=self.generate_keyboard())

    async def handle_continue_later(self, update: Update, user_to_state: UsersToState) -> None:
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.CONTINUE_LATER,
                                                 update.effective_user.first_name)

    #############
    # UTILITIES #
    #############

    def generate_keyboard(self) -> [[str]]:
        all_commands = list(self.transitions.keys())
        return [[x] for x in all_commands]
