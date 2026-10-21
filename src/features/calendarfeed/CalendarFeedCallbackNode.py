import logging

from telegram import Update

from Enums import Audience
from Enums.MessageType import MessageType

from framework.Nodes.CallbackNode import CallbackNode

from features.calendarfeed import CalendarFeedMenu
from features.calendarfeed.CalendarFeedReplies import send_link_overview
from features.calendarfeed.CalendarFeedService import CalendarFeedService


class CalendarFeedCallbackNode(CallbackNode):
    """CAL# taps: the 📆 row in the events list (SHOW) and 🔄 on a link or status message
    (ROTATE). Answers with a new message, so the events list stays where it was."""

    # Same audience as the events menu that offers the row.
    audience = Audience.EVERYONE

    def __init__(self, telegram_service, data_access, trigger_service, calendar_feed_service: CalendarFeedService):
        super().__init__(telegram_service, data_access, trigger_service)
        self.calendar_feed_service = calendar_feed_service

    async def handle(self, update: Update):
        query = update.callback_query
        await query.answer()
        try:
            action = CalendarFeedMenu.decode(query.data)
            if action is None:
                return
            await send_link_overview(self.telegram_service, self.calendar_feed_service, update,
                                     update.effective_chat.id, rotate=action == CalendarFeedMenu.ROTATE)
        except Exception as e:
            # No update on purpose: NodeHandler would report str(update), and the tapped message is the
            # DM carrying the raw calendar link - the token must never reach the maintainer chat.
            await self.telegram_service.report_exception('Exception in CalendarFeedCallbackNode.handle', e)
            await self._tell_user_it_failed(update)

    async def _tell_user_it_failed(self, update: Update):
        try:
            await self.telegram_service.send_message(update=update, all_buttons=None,
                                                     message_type=MessageType.ERROR)
        except Exception:
            logging.warning('Could not send the calendar error reply', exc_info=True)
