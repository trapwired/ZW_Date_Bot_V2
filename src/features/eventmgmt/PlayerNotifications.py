"""Pushes an event with attendance buttons to every player - the shared tail of the
'new event added' and 'event moved' notifications, kept in one place so the two
pushed messages can't drift apart."""
from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.MessageType import MessageType

from features.events import EventsMenu

from framework.RecipientLanguage import recipient_language_context

from Utils import PrintUtils


async def push_event_to_players(telegram_service, data_access, players: list, event, event_type: Event,
                                intro_message_type: MessageType, intro_extra_text: str = '') -> None:
    reply_markup = EventsMenu.build_attendance_markup(event_type, event.doc_id)

    for player in players:
        # Composed inside the loop: intro and event text must render in each
        # recipient's language, not the acting admin's.
        with recipient_language_context(data_access, player.telegramId):
            pretty_print_event = PrintUtils.pretty_print(event, AttendanceState.UNSURE)
            message_text = PrintUtils.event_label(event_type) + ' | ' + pretty_print_event
            await telegram_service.send_message(
                update=player,
                all_buttons=None,
                message_type=intro_message_type,
                message_extra_text=intro_extra_text)
            await telegram_service.send_message(
                update=player,
                all_buttons=None,
                message=message_text,
                reply_markup=reply_markup)
