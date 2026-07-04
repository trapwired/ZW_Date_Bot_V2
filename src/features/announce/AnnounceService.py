"""Application service for the admin announcement slice: renders the message once
and owns the two delivery channels (private fan-out / team group chat)."""
import logging

from telegram.error import TelegramError

from data.DataAccess import DataAccess

from framework.Services.TelegramService import TelegramService

from Utils import Format


def render_announcement(text: str) -> str:
    return Format.bold('📣 Announcement') + '\n' + Format.escape(text)


class AnnounceService:
    def __init__(self, data_access: DataAccess, telegram_service: TelegramService):
        self.data_access = data_access
        self.telegram_service = telegram_service

    async def send_to_players(self, text: str) -> int:
        """Fan the announcement out to every active player (admins included) as a
        private message. Best-effort per recipient: one unreachable player (blocked
        bot, deleted account) must not stop the broadcast. Returns the reached count."""
        message = render_announcement(text)
        reached = 0
        for player in self.data_access.get_all_players():
            try:
                await self.telegram_service.send_message(update=player, all_buttons=None, message=message)
                reached += 1
            except TelegramError as e:
                logging.info(f'Announcement could not reach player {player.telegramId}: {e}')
        return reached

    async def send_to_group(self, text: str) -> None:
        await self.telegram_service.send_group_message(render_announcement(text))
