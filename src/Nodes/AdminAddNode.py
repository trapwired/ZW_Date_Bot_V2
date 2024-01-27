from telegram import Update

from Nodes.Node import Node

from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption

from databaseEntities.UsersToState import UsersToState
from databaseEntities.TempData import TempData

from Utils import UpdateEventUtils
from Utils import PrintUtils
from Utils import CallbackUtils


def get_reply_markup_user_state(event_type: Event):
    match event_type:
        case Event.GAME:
            return UserState.ADMIN_ADD_GAME
        case Event.TRAINING:
            return UserState.ADMIN_ADD_TRAINING
        case Event.TIMEKEEPING:
            return UserState.ADMIN_ADD_TIMEKEEPING


def get_first_add_user_state(event_type: Event):
    match event_type:
        case Event.GAME:
            return UserState.ADMIN_ADD_GAME_TIMESTAMP
        case Event.TRAINING:
            return UserState.ADMIN_ADD_TRAINING_TIMESTAMP
        case Event.TIMEKEEPING:
            return UserState.ADMIN_ADD_TIMEKEEPING_TIMESTAMP


class AdminAddNode(Node):

    async def handle_add_game(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self._handle_add_event(Event.GAME, update, user_to_state)

    async def handle_add_training(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self._handle_add_event(Event.TRAINING, update, user_to_state)

    async def handle_add_timekeeping(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self._handle_add_event(Event.TIMEKEEPING, update, user_to_state)

    async def _handle_add_event(self, event_type, update, user_to_state):
        temp_date = TempData(user_to_state.user_id, event_type) # to delete
        temp_data = self.data_access.add(temp_date)
        event_summary = PrintUtils.pretty_print(temp_data, event_type)
        pretty_print = UpdateEventUtils.get_inline_message('Adding new', event_type, event_summary)
        reply_markup = CallbackUtils.get_add_event_reply_markup(get_reply_markup_user_state(event_type), event_type,
                                                                temp_data.doc_id)
        query = await self.telegram_service.send_message(update=update, all_buttons=[], reply_markup=reply_markup,
                                                         message=pretty_print)
        temp_data = temp_data.add_inline_information(query.chat.id, query.id)
        self.data_access.update(temp_data)
        self.user_state_service.update_user_state(user_to_state, get_first_add_user_state(event_type))
        message = PrintUtils.get_update_attribute_message(CallbackOption.DATETIME)
        await self.telegram_service.send_message_with_normal_keyboard(update=update, message=message)
