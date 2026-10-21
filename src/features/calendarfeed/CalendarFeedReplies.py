"""The calendar subscription's bot replies, shared by both entry points (the 📆 row in
the events list and /calendar) so they can't drift apart (plan §7)."""
import logging

from telegram import Update

from Utils import Format

from features.calendarfeed import CalendarFeedMenu
from features.calendarfeed.CalendarFeedService import CalendarFeedService, IssuedLink, LinkStatus

from localization.Translator import t

DATE_FORMAT = '%d.%m.%Y'


async def send_link_overview(telegram_service, calendar_feed_service: CalendarFeedService, update: Update,
                             telegram_id: int, *, rotate: bool) -> None:
    """First request (or 🔄): issue a link and explain how to subscribe. Later requests:
    only the link's status - the raw token is gone once sent (only its hash is stored)."""
    if not calendar_feed_service.enabled:
        await _send(telegram_service, update, t('The calendar subscription is not set up on this bot.'))
        return
    status = None if rotate else calendar_feed_service.link_status(telegram_id)
    if status is None:
        await _send_link(telegram_service, telegram_id, calendar_feed_service.issue_link(telegram_id))
        return
    await _send(telegram_service, update, _status_text(status), CalendarFeedMenu.build_rotate_markup())


def _link_text(link: IssuedLink) -> str:
    return '\n\n'.join([
        t('📆 Your personal calendar link - tap it to copy:') + '\n' + Format.code(link.url),
        t('<b>iPhone:</b> Calendar app › Calendars › Add Calendar › Add Subscription Calendar › paste the link.'),
        t('<b>Android:</b> on a computer, open calendar.google.com › Other calendars + › From URL and paste '
          'the link - or use the button below.'),
        t('Changes reach your calendar with a delay: a few hours, Google Calendar up to a day.'),
        t('The link is personal: whoever has it sees your calendar. 🔄 creates a new one, and the old one '
          'stops working at once.'),
    ])


def _status_text(status: LinkStatus) -> str:
    fetched = status.last_used_at.strftime(DATE_FORMAT) if status.last_used_at is not None else t('never')
    return (t('You already have a calendar link (created {created}, last fetched: {fetched}).',
              created=status.created_at.strftime(DATE_FORMAT), fetched=fetched)
            + '\n\n'
            + t("I can't show it again - I only keep a fingerprint of it. 🔄 creates a new one, and the old "
                "one stops working at once."))


async def _send_link(telegram_service, telegram_id: int, link: IssuedLink) -> None:
    # Not _send: on Forbidden / chat-not-found TelegramService._send_message echoes the text into a
    # maintainer alert, and this text carries the raw calendar link. Failure is logged without content.
    try:
        await telegram_service.send_message_or_raise(
            telegram_id, _link_text(link), reply_markup=CalendarFeedMenu.build_link_markup(link.google_url))
    except Exception:
        logging.warning('Could not deliver the calendar link to %s', telegram_id)


async def _send(telegram_service, update: Update, text: str, reply_markup=None) -> None:
    await telegram_service.send_message(update=update, all_buttons=None, message=text, reply_markup=reply_markup)
