from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption
from Enums.AttendanceState import AttendanceState
from Enums.AddEventMarkup import AddEventMarkup

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
        temp_data = self.data_access.get_temp_data(user_to_state.user_id)
        self.data_access.delete(temp_data)
        self.user_state_service.update_user_state(user_to_state, new_state)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN)

    async def handle_user_input(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        match self.event_type:
            case Event.GAME:
                await self.handle_game_flow(update, user_to_state, new_state)
            case Event.TRAINING:
                await self.handle_training_flow(update, user_to_state, new_state)
            case Event.TIMEKEEPING:
                await self.handle_timekeeping_flow(update, user_to_state, new_state)

    async def handle_save(self, new_state, temp_data, update, user_to_state):
        new_game = self.data_access.add(temp_data.get_finished_event())
        await self.update_inline_message(temp_data, 'Saved', AddEventMarkup.NONE)
        self.data_access.delete(temp_data)
        self.node_handler.recalculate_node_transitions()
        await self.notify_all_players(new_game)
        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.node_handler.get_node(UserState.ADMIN).get_commands_for_buttons(
                user_to_state.role, new_state,
                update.effective_chat.id),
            message_type=MessageType.ADMIN)

    async def update_inline_message(self, temp_data, prefix, markup_type: AddEventMarkup):
        event_summary = PrintUtils.pretty_print(temp_data, self.event_type)
        pretty_print = UpdateEventUtils.get_inline_message(prefix, self.event_type, event_summary)

        match markup_type:
            case AddEventMarkup.DEFAULT:
                reply_markup = CallbackUtils.get_add_event_reply_markup(UserState.ADMIN_ADD_GAME, Event.GAME,
                                                                        temp_data.doc_id)
                pass
            case AddEventMarkup.SAVE:
                reply_markup = CallbackUtils.get_finish_add_event_reply_markup(UserState.ADMIN_ADD_GAME, Event.GAME,
                                                                               temp_data.doc_id)
                pass
            case _:
                reply_markup = None

        await self.telegram_service.edit_inline_message_text(pretty_print, temp_data.query_id, temp_data.chat_id,
                                                             reply_markup)

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

                await self.update_inline_message(temp_data, 'Adding new', AddEventMarkup.DEFAULT)

            case UserState.ADMIN_ADD_GAME_LOCATION:
                temp_data.location = message
                self.data_access.update(temp_data)

                next_attribute = CallbackOption.OPPONENT
                next_state = UserState.ADMIN_ADD_GAME_OPPONENT

                await self.update_inline_message(temp_data, 'Adding new', AddEventMarkup.DEFAULT)

            case UserState.ADMIN_ADD_GAME_OPPONENT:
                temp_data.opponent = message
                self.data_access.update(temp_data)

                await self.update_inline_message(temp_data, 'Adding new', AddEventMarkup.SAVE)

                next_attribute = CallbackOption.SAVE
                next_state = UserState.ADMIN_FINISH_ADD_GAME

            case UserState.ADMIN_FINISH_ADD_GAME:
                if message == 'save':
                    await self.handle_save(new_state, temp_data, update, user_to_state)
                    return
                else:
                    next_attribute = CallbackOption.SAVE
                    next_state = UserState.ADMIN_FINISH_ADD_GAME

        # send next instruction
        message = PrintUtils.get_update_attribute_message(next_attribute)
        await self.telegram_service.send_message_with_normal_keyboard(update=update, message=message)

        # update userState to next one
        self.user_state_service.update_user_state(user_to_state, next_state)

    async def handle_training_flow(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        message = update.message.text.lower()
        temp_data = self.data_access.get_temp_data(user_to_state.user_id)

        match user_to_state.state:
            case UserState.ADMIN_ADD_TRAINING_TIMESTAMP:
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
                next_state = UserState.ADMIN_ADD_TRAINING_LOCATION

                await self.update_inline_message(temp_data, 'Adding new', AddEventMarkup.DEFAULT)

            case UserState.ADMIN_ADD_TRAINING_LOCATION:
                temp_data.location = message
                self.data_access.update(temp_data)

                await self.update_inline_message(temp_data, 'Adding new', AddEventMarkup.SAVE)

                next_attribute = CallbackOption.SAVE
                next_state = UserState.ADMIN_FINISH_ADD_TRAINING

            case UserState.ADMIN_FINISH_ADD_TRAINING:
                if message == 'save':
                    await self.handle_save(new_state, temp_data, update, user_to_state)
                    return
                else:
                    next_attribute = CallbackOption.SAVE
                    next_state = UserState.ADMIN_FINISH_ADD_TRAINING

        # send next instruction
        message = PrintUtils.get_update_attribute_message(next_attribute)
        await self.telegram_service.send_message_with_normal_keyboard(update=update, message=message)

        # update userState to next one
        self.user_state_service.update_user_state(user_to_state, next_state)

    async def handle_timekeeping_flow(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        message = update.message.text.lower()
        temp_data = self.data_access.get_temp_data(user_to_state.user_id)

        match user_to_state.state:
            case UserState.ADMIN_ADD_TIMEKEEPING_TIMESTAMP:
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
                next_state = UserState.ADMIN_ADD_TIMEKEEPING_LOCATION

                await self.update_inline_message(temp_data, 'Adding new', AddEventMarkup.DEFAULT)

            case UserState.ADMIN_ADD_TIMEKEEPING_LOCATION:
                temp_data.location = message
                self.data_access.update(temp_data)

                await self.update_inline_message(temp_data, 'Adding new', AddEventMarkup.SAVE)

                next_attribute = CallbackOption.SAVE
                next_state = UserState.ADMIN_FINISH_ADD_TIMEKEEPING

            case UserState.ADMIN_FINISH_ADD_TIMEKEEPING:
                if message == 'save':
                    await self.handle_save(new_state, temp_data, update, user_to_state)
                    return
                else:
                    next_attribute = CallbackOption.SAVE
                    next_state = UserState.ADMIN_FINISH_ADD_TIMEKEEPING

        # send next instruction
        message = PrintUtils.get_update_attribute_message(next_attribute)
        await self.telegram_service.send_message_with_normal_keyboard(update=update, message=message)

        # update userState to next one
        self.user_state_service.update_user_state(user_to_state, next_state)

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        # use default transition for anything that can't be predicted
        await self.handle_user_input(update, user_to_state, new_state)

    async def handle_parse_additional_info_failed(self, user_to_state: UsersToState, update: Update):
        text = 'Error getting information from the database, please restart adding an event via the menu :)'
        await self.telegram_service.send_message_with_normal_keyboard(
            update=update,
            message=text)

        await self.handle_cancel(update, user_to_state, UserState.ADMIN)

    async def notify_all_players(self, new_event):
        all_players = self.data_access.get_all_players()

        for player in all_players:
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message_type=MessageType.EVENT_ADDED)

            pretty_print_event = PrintUtils.pretty_print(new_event, AttendanceState.UNSURE)
            reply_markup = CallbackUtils.get_edit_event_reply_markup(
                UserState.EDIT,
                self.event_type,
                new_event.doc_id)
            message_text = self.event_type.name.lower().title() + ' | ' + pretty_print_event
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message=message_text,
                reply_markup=reply_markup)
