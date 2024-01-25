from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption

from databaseEntities.UsersToState import UsersToState
from databaseEntities.TempData import TempData

from Utils import UpdateEventUtils
from Utils import PrintUtils
from Utils import CallbackUtils


class AdminAddNode(Node):

    async def handle_add_game(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # TODO make generic method, handle_add_event (event_type...)  + call from 3 methods
        event_type = Event.GAME
        temp_data = self.data_access.add(TempData(user_to_state.user_id))
        event_summary = PrintUtils.pretty_print(temp_data, event_type)
        pretty_print = UpdateEventUtils.get_inline_message('Adding new', event_type, event_summary)

        reply_markup = CallbackUtils.get_add_event_reply_markup(UserState.ADMIN_ADD_GAME, Event.GAME, temp_data.doc_id)

        query = await self.telegram_service.send_message(update=update, all_buttons=[], reply_markup=reply_markup,
                                                         message=pretty_print)

        temp_data = temp_data.add_inline_information(query.chat.id, query.id)
        self.data_access.update(temp_data)

        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN_ADD_GAME_TIMESTAMP)

        message = PrintUtils.get_update_attribute_message(CallbackOption.DATETIME)
        await self.telegram_service.send_message_with_normal_keyboard(update=update, message=message)

    async def handle_add_training(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADD)

    async def handle_add_timekeeping(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADD)
