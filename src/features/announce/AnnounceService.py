"""Application service for the admin announcement slice: renders the message once
and owns the two delivery channels (private fan-out / team group chat)."""
import logging

from telegram.error import TelegramError

from data.DataAccess import DataAccess

from framework.Services.TelegramService import TelegramService

from Utils import Format


# Telegram rejects messages above this length; the rendered announcement (header +
# HTML-escaped text, where e.g. '<' inflates to '&lt;') must stay below it.
TELEGRAM_MESSAGE_LIMIT = 4096


def render_announcement(text: str) -> str:
    return Format.bold('📣 Announcement') + '\n' + Format.escape(text)


class AnnounceService:
    def __init__(self, data_access: DataAccess, telegram_service: TelegramService):
        self.data_access = data_access
        self.telegram_service = telegram_service

    async def send_to_players(self, text: str) -> int:
        """Fan the announcement out to every active player (admins included) as a
        private message. Best-effort per recipient: one unreachable player must not
        stop the broadcast. Returns the reached count - Forbidden (blocked bot) is
        swallowed inside _send_message and surfaces as a None result, so only a real
        send counts."""
        message = self._render_checked(text)
        reached = 0
        for player in self.data_access.get_all_players():
            try:
                if await self.telegram_service.send_message(update=player, all_buttons=None,
                                                            message=message) is not None:
                    reached += 1
            except TelegramError as e:
                logging.info(f'Announcement could not reach player {player.telegramId}: {e}')
        return reached

    async def send_to_group(self, text: str) -> None:
        await self.telegram_service.send_group_message(self._render_checked(text))

    @staticmethod
    def _render_checked(text: str) -> str:
        # Both invariants the UI already enforces, re-enforced at the source so a
        # future caller can't broadcast an empty header or a Telegram-rejected length.
        if not text.strip():
            raise ValueError('Announcement text must not be empty')
        message = render_announcement(text)
        if len(message) > TELEGRAM_MESSAGE_LIMIT:
            raise ValueError('Announcement exceeds the Telegram message limit')
        return message
