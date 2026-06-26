from telegram import Update

from Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils

from Enums.CallbackOption import CallbackOption
from Enums.RoleSet import RoleSet


class ResetStatisticsCallbackNode(CallbackNode):
    required_roles = RoleSet.ADMINS

    async def handle(self, update: Update):
        query = update.callback_query
        _, _, callback_option, _ = CallbackUtils.try_parse_callback_message(query.data)

        await query.answer()

        match callback_option:
            case CallbackOption.YES:
                deleted_count = self.data_access.reset_statistics()
                message = (f'Done - the season has ended. Reminder statistics were reset for all '
                           f'players ({deleted_count} entries removed).')
            case CallbackOption.NO:
                message = 'Cancelled - no statistics were reset.'
            case _:
                return

        await self.telegram_service.edit_callback_message(query, message)
