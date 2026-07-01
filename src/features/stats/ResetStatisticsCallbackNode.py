from telegram import Update

from Nodes.CallbackNode import CallbackNode

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService
from Data.DataAccess import DataAccess

from Utils import CallbackUtils

from Enums.CallbackOption import CallbackOption
from Enums.RoleSet import RoleSet


class ResetStatisticsCallbackNode(CallbackNode):
    required_roles = RoleSet.ADMINS

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 statistics_service):
        super().__init__(telegram_service, data_access, trigger_service)
        self.statistics_service = statistics_service

    async def handle(self, update: Update):
        query = update.callback_query
        _, _, callback_option, _ = CallbackUtils.try_parse_callback_message(query.data)

        await query.answer()

        match callback_option:
            case CallbackOption.YES:
                deleted_count = self.statistics_service.reset_reminder_statistics()
                message = (f'Done - the season has ended. Reminder statistics were reset for all '
                           f'players ({deleted_count} entries removed).')
            case CallbackOption.NO:
                message = 'Cancelled - no statistics were reset.'
            case _:
                return

        await self.telegram_service.edit_callback_message(query, message)
