from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption

from databaseEntities.UsersToState import UsersToState
from databaseEntities.Game import Game

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
        temp_data = self.data_access.get_temp_data(user_to_state.user_id)
        self.data_access.delete(temp_data)
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
        message = update.message.text.lower()
        temp_data = self.data_access.get_temp_data(user_to_state.user_id)

        match user_to_state.state:
            case UserState.ADMIN_ADD_GAME_TIMESTAMP:
                parsed_datetime = UpdateEventUtils.parse_datetime_string(message)
                if type(parsed_datetime) is str:
                    # Error case, send message without changing anything
                    await self.telegram_service.send_message_with_normal_keyboard(
                        update=update,
                        message=parsed_datetime)
                    return

                temp_data.timestamp = parsed_datetime
                self.data_access.update(temp_data)

                next_attribute = CallbackOption.LOCATION
                next_state = UserState.ADMIN_ADD_GAME_LOCATION

                await self.update_inline_message(temp_data, 'Adding new')

            case UserState.ADMIN_ADD_GAME_LOCATION:
                temp_data.location = message
                self.data_access.update(temp_data)

                next_attribute = CallbackOption.OPPONENT
                next_state = UserState.ADMIN_ADD_GAME_OPPONENT

                await self.update_inline_message(temp_data, 'Adding new')

            case UserState.ADMIN_ADD_GAME_OPPONENT:
                temp_data.opponent = message

                await self.update_inline_message(temp_data, 'Adding new', add_save_reply_markup=True)

                next_attribute = CallbackOption.SAVE
                next_state = UserState.ADMIN_FINISH_ADD_GAME
                # notify everyone
                pass
            case UserState.ADMIN_FINISH_ADD_GAME:
                if message == 'save':
                    new_game = self.data_access.add(Game(temp_data.get_game_parameters()))

                    # edit inline_message: remove buttons
                    await self.update_inline_message(temp_data, 'Saved')
                    # notify everyone
                    # TODO get rid of reply markup


                    return
                else:
                    next_attribute = CallbackOption.SAVE
                    next_state = UserState.ADMIN_FINISH_ADD_GAME

        # send next instruction
        message = PrintUtils.get_update_attribute_message(next_attribute)
        await self.telegram_service.send_message_with_normal_keyboard(update=update, message=message)

        # update userState to next one
        self.user_state_service.update_user_state(user_to_state, next_state)

    async def update_inline_message(self, temp_data, prefix, add_save_reply_markup=False):
        event_summary = PrintUtils.pretty_print(temp_data, self.event_type)
        pretty_print = UpdateEventUtils.get_inline_message(prefix, self.event_type, event_summary)
        reply_markup = CallbackUtils.get_finish_add_event_reply_markup(UserState.ADMIN_ADD_GAME, Event.GAME,
                                                                       temp_data.doc_id) if add_save_reply_markup else None
        # TODO get rid of reply markup / handle correctly
        await self.telegram_service.edit_inline_message_text(pretty_print, temp_data.query_id, temp_data.chat_id,
                                                             reply_markup)

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
