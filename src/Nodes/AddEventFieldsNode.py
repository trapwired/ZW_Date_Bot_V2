from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption

from databaseEntities.UsersToState import UsersToState

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService

from Utils import UpdateEventUtils
from Utils import PrintUtils
from Utils import CallbackUtils


class AddEventFieldsNode(Node):
    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, event_type: Event, node_handler):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.event_type = event_type
        self.add_cancel_transition()
        self.node_handler = node_handler

    def add_cancel_transition(self):
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.ADMIN)

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, new_state)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN)

    async def handle_user_input(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        # TODO hier ausrechnen, was in jedem flow gebraucht wird
        match self.event_type:
            case Event.GAME:
                await self.handle_game_flow(update, user_to_state, new_state)
            case Event.TRAINING:
                await self.handle_training_flow(update, user_to_state, new_state)
            case Event.TIMEKEEPING:
                await self.handle_timekeeping_flow(update, user_to_state, new_state)

    async def handle_game_flow(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # tryparse date or string
        # how to update user_state?
        # always resend callback (if so, delete old one)
        # send format / expcted + always /cancel
        # TODO set correct states
        match user_to_state.state:
            case UserState.ADMIN_ADD_GAME_TIMESTAMP:
                # TryParse Datetime
                message = update.message.text.lower()

                parsed_datetime = UpdateEventUtils.parse_datetime_string(message)
                if type(parsed_datetime) is str:
                    # Error case, send message without changing anything
                    await self.telegram_service.send_message_with_normal_keyboard(
                        update=update,
                        message=parsed_datetime)
                    return

                new_datetime = parsed_datetime

                try_parse = CallbackUtils.try_parse_additional_information(user_to_state.additional_info)
                if not try_parse:
                    return await self.handle_parse_additional_info_failed(user_to_state, update)

                message_id, chat_id, doc_id = try_parse

                # if ok, update inline message

                # send next anweisung

                # update userState to next one

    async def handle_training_flow(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        match user_to_state.state:
            case UserState.ADMIN_ADD_TRAINING:
                pass

    async def handle_timekeeping_flow(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        match user_to_state.state:
            case UserState.ADMIN_ADD_TIMEKEEPING:
                pass

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        # use default transition for anything that can't be predicted
        await self.handle_user_input(update, user_to_state, new_state)

    async def handle_parse_additional_info_failed(self, user_to_state: UsersToState, update: Update):
        text = 'Error getting information from the database, please restart adding an event via the menu :)'
        await self.telegram_service.send_message_with_normal_keyboard(
            update=update,
            message=text)

        await self.handle_cancel(update, user_to_state, UserState.ADMIN)
