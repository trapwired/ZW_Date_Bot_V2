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

from domain import EventDateTimeParser


# Ordered field-collection steps per event type. The only thing that differs
# between game/training/timekeeping is this list (games additionally collect an
# opponent), so a single flow walks it instead of three copy-pasted handlers.
_ADD_STEPS = {
    Event.GAME: [
        (UserState.ADMIN_ADD_GAME_TIMESTAMP, CallbackOption.DATETIME),
        (UserState.ADMIN_ADD_GAME_LOCATION, CallbackOption.LOCATION),
        (UserState.ADMIN_ADD_GAME_OPPONENT, CallbackOption.OPPONENT),
    ],
    Event.TRAINING: [
        (UserState.ADMIN_ADD_TRAINING_TIMESTAMP, CallbackOption.DATETIME),
        (UserState.ADMIN_ADD_TRAINING_LOCATION, CallbackOption.LOCATION),
    ],
    Event.TIMEKEEPING: [
        (UserState.ADMIN_ADD_TIMEKEEPING_TIMESTAMP, CallbackOption.DATETIME),
        (UserState.ADMIN_ADD_TIMEKEEPING_LOCATION, CallbackOption.LOCATION),
    ],
}

_FINISH_STATE = {
    Event.GAME: UserState.ADMIN_FINISH_ADD_GAME,
    Event.TRAINING: UserState.ADMIN_FINISH_ADD_TRAINING,
    Event.TIMEKEEPING: UserState.ADMIN_FINISH_ADD_TIMEKEEPING,
}

# The UserState encoded into the inline-keyboard callback channel for the add flow.
_ADD_USER_STATE = {
    Event.GAME: UserState.ADMIN_ADD_GAME,
    Event.TRAINING: UserState.ADMIN_ADD_TRAINING,
    Event.TIMEKEEPING: UserState.ADMIN_ADD_TIMEKEEPING,
}


class AddEventFieldsNode(Node):
    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, event_type: Event, node_handler, event_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.event_type = event_type
        self.add_cancel_transition()
        self.node_handler = node_handler
        self.event_service = event_service

    def add_cancel_transition(self):
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.ADMIN)

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        temp_data = self.event_service.get_draft(user_to_state.user_id)
        self.event_service.discard_draft(temp_data)
        self.user_state_service.update_user_state(user_to_state, new_state)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN)

    async def handle_user_input(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        message = update.message.text.lower()
        temp_data = self.event_service.get_draft(user_to_state.user_id)
        finish_state = _FINISH_STATE[self.event_type]

        # On the finish step, 'save' commits; anything else just re-prompts to save.
        if user_to_state.state == finish_state:
            if message == 'save':
                await self.handle_save(new_state, temp_data, update, user_to_state)
                return
            await self._prompt_next(update, user_to_state, CallbackOption.SAVE, finish_state)
            return

        steps = _ADD_STEPS[self.event_type]
        index = self._step_index(steps, user_to_state.state)
        _, field = steps[index]

        if field == CallbackOption.DATETIME:
            parsed = EventDateTimeParser.parse_future(message)
            if not parsed.ok:
                # Parsing failed - report and stay on this step without mutating anything.
                await self.telegram_service.send_message_with_normal_keyboard(update=update, message=parsed.error)
                return
            temp_data.timestamp = parsed.value
        elif field == CallbackOption.LOCATION:
            temp_data.location = message
        elif field == CallbackOption.OPPONENT:
            temp_data.opponent = message
        self.event_service.save_draft(temp_data)

        if index + 1 < len(steps):
            next_state, next_attribute = steps[index + 1]
            markup = AddEventMarkup.DEFAULT
        else:
            next_state, next_attribute = finish_state, CallbackOption.SAVE
            markup = AddEventMarkup.SAVE

        await self.update_inline_message(temp_data, 'Adding new', markup)
        await self._prompt_next(update, user_to_state, next_attribute, next_state)

    @staticmethod
    def _step_index(steps, state: UserState) -> int:
        for index, (step_state, _) in enumerate(steps):
            if step_state == state:
                return index
        raise ValueError(f'No add-event step for state {state}')

    async def _prompt_next(self, update: Update, user_to_state: UsersToState, attribute: CallbackOption,
                           next_state: UserState) -> None:
        message = PrintUtils.get_update_attribute_message(attribute)
        await self.telegram_service.send_message_with_normal_keyboard(update=update, message=message)
        self.user_state_service.update_user_state(user_to_state, next_state)

    async def handle_save(self, new_state, temp_data, update, user_to_state):
        new_game = self.event_service.finalize_draft(temp_data)
        await self.update_inline_message(temp_data, 'Saved', AddEventMarkup.NONE)
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

        user_state = _ADD_USER_STATE[self.event_type]
        match markup_type:
            case AddEventMarkup.DEFAULT:
                reply_markup = CallbackUtils.get_add_event_reply_markup(user_state, self.event_type, temp_data.doc_id)
            case AddEventMarkup.SAVE:
                reply_markup = CallbackUtils.get_finish_add_event_reply_markup(user_state, self.event_type,
                                                                               temp_data.doc_id)
            case _:
                reply_markup = None

        await self.telegram_service.edit_inline_message_text(pretty_print, temp_data.query_id, temp_data.chat_id,
                                                             reply_markup)

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
        all_players = self.event_service.get_all_players()

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
            message_text = PrintUtils.event_label(self.event_type) + ' | ' + pretty_print_event
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message=message_text,
                reply_markup=reply_markup)
