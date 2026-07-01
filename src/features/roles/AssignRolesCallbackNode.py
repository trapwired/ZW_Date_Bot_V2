import logging

from telegram import Update
from telegram.error import TelegramError

from data.DataAccess import DataAccess

from Enums.Role import Role
from Enums.RoleSet import RoleSet
from Enums.UserState import UserState

from framework.Nodes.CallbackNode import CallbackNode

from framework.Services.TelegramService import TelegramService
from framework.Services.TriggerService import TriggerService
from framework.Services.UserStateService import UserStateService

from Utils import PrintUtils
from features.roles import RoleAssignment
from Utils import Format


class AssignRolesCallbackNode(CallbackNode):
    required_roles = RoleSet.ADMINS

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 user_state_service: UserStateService, node_handler, role_service):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service
        self.node_handler = node_handler
        self.role_service = role_service

    async def handle(self, update: Update):
        query = update.callback_query
        await query.answer()

        parsed = RoleAssignment.parse(query.data)
        if parsed is None:
            return
        action, args = parsed

        match action:
            case RoleAssignment.HOME:
                await self._show_overview(query)
            case RoleAssignment.LIST_USERS:
                await self._show_user_list(query, Role(int(args[0])))
            case RoleAssignment.SELECT_USER:
                await self._show_assign_options(query, args[0])
            case RoleAssignment.ASSIGN:
                await self._assign_role(query, args[0], Role(int(args[1])))

    async def _show_overview(self, query):
        counts = self.role_service.role_counts()
        await self.telegram_service.edit_callback_message(
            query, Format.bold('Select a role to manage:'),
            reply_markup=RoleAssignment.build_overview_markup(counts))

    async def _show_user_list(self, query, role: Role):
        users = self.role_service.users_with_role(role)
        if len(users) == 0:
            await self.telegram_service.edit_callback_message(
                query, f'No users currently have the role {Format.bold(role.name)}.',
                reply_markup=RoleAssignment.build_home_markup())
            return

        entries = [(user_doc_id, PrintUtils.get_player_display_name(user), role)
                   for user_doc_id, user in users]
        await self.telegram_service.edit_callback_message(
            query, f'Users with role {Format.bold(role.name)} - tap one to change it:',
            reply_markup=RoleAssignment.build_user_list_markup(entries))

    async def _show_assign_options(self, query, user_doc_id: str):
        user, user_to_state = self.role_service.get_user_and_state(user_doc_id)
        name = Format.bold(PrintUtils.get_player_display_name(user))
        await self.telegram_service.edit_callback_message(
            query, f'{name} is currently {Format.bold(user_to_state.role.name)}. Assign a new role:',
            reply_markup=RoleAssignment.build_assign_markup(user_doc_id, user_to_state.role))

    async def _assign_role(self, query, user_doc_id: str, new_role: Role):
        user = self.role_service.assign_role(user_doc_id, new_role)

        notified = await self._notify_user(user, new_role)

        name = Format.bold(PrintUtils.get_player_display_name(user))
        text = f'✅ {name} is now {Format.bold(new_role.name)}.'
        if not notified:
            text += '\nCould not notify them - they may have removed Telegram.'
        await self.telegram_service.edit_callback_message(query, text, reply_markup=RoleAssignment.build_home_markup())

    async def _notify_user(self, user, new_role: Role) -> bool:
        # Best-effort: the role change is already persisted, so a user we can no longer reach
        # (deleted account, blocked bot) must not fail the whole flow.
        default_node = self.node_handler.get_node(UserState.DEFAULT)
        buttons = default_node.get_commands_for_buttons(new_role, UserState.DEFAULT, user.telegramId)
        try:
            await self.telegram_service.send_message(
                update=user,
                all_buttons=buttons,
                message=f'An admin set your role to {Format.bold(new_role.name)}.')
            return True
        except TelegramError as e:
            logging.info(f'Could not notify user {user.telegramId} of role change: {e}')
            return False
