import logging

from telegram import Update
from telegram.error import TelegramError

from Data.DataAccess import DataAccess

from Enums.Role import Role, ASSIGNABLE_ROLES
from Enums.UserState import UserState

from Nodes.CallbackNode import CallbackNode

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService
from Services.UserStateService import UserStateService

from Utils import PrintUtils
from Utils import RoleAssignment


class AssignRolesCallbackNode(CallbackNode):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 user_state_service: UserStateService, node_handler):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service
        self.node_handler = node_handler

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
        counts = {role: self.data_access.get_role_user_count(role) for role in ASSIGNABLE_ROLES}
        await query.edit_message_text(
            text='Select a role to manage:',
            reply_markup=RoleAssignment.build_overview_markup(counts))

    async def _show_user_list(self, query, role: Role):
        users_to_state = self.data_access.get_users_to_state_by_role(role)
        if len(users_to_state) == 0:
            await query.edit_message_text(
                text=f'No users currently have the role {role.name}.',
                reply_markup=RoleAssignment.build_home_markup())
            return

        users = self.data_access.add_names([uts.user_id for uts in users_to_state])
        entries = [(uts.user_id, PrintUtils.get_player_display_name(user), role)
                   for uts, user in zip(users_to_state, users)]
        await query.edit_message_text(
            text=f'Users with role {role.name} - tap one to change it:',
            reply_markup=RoleAssignment.build_user_list_markup(entries))

    async def _show_assign_options(self, query, user_doc_id: str):
        user = self.data_access.get_user_by_doc_id(user_doc_id)
        user_to_state = self.data_access.get_user_state_for_user(user)
        name = PrintUtils.get_player_display_name(user)
        await query.edit_message_text(
            text=f'{name} is currently {user_to_state.role.name}. Assign a new role:',
            reply_markup=RoleAssignment.build_assign_markup(user_doc_id, user_to_state.role))

    async def _assign_role(self, query, user_doc_id: str, new_role: Role):
        user = self.data_access.get_user_by_doc_id(user_doc_id)
        user_to_state = self.data_access.get_user_state_for_user(user)

        user_to_state.add_role(new_role)
        # Their previous bot state may no longer be valid for the new role - send them back to the
        # main menu so the next interaction rebuilds the correct one.
        user_to_state.state = UserState.DEFAULT
        self.data_access.update(user_to_state)

        notified = await self._notify_user(user, new_role)

        name = PrintUtils.get_player_display_name(user)
        text = f'✓ {name} is now {new_role.name}.'
        if not notified:
            text += '\nCould not notify them - they may have removed Telegram.'
        await query.edit_message_text(text=text, reply_markup=RoleAssignment.build_home_markup())

    async def _notify_user(self, user, new_role: Role) -> bool:
        # Best-effort: the role change is already persisted, so a user we can no longer reach
        # (deleted account, blocked bot) must not fail the whole flow.
        default_node = self.node_handler.get_node(UserState.DEFAULT)
        buttons = default_node.get_commands_for_buttons(new_role, UserState.DEFAULT, user.telegramId)
        try:
            await self.telegram_service.send_message(
                update=user,
                all_buttons=buttons,
                message=f'An admin set your role to {new_role.name}.')
            return True
        except TelegramError as e:
            logging.info(f'Could not notify user {user.telegramId} of role change: {e}')
            return False
