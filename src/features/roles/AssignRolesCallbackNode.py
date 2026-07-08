import logging

from telegram import Update
from telegram.error import TelegramError

from data.DataAccess import DataAccess

from Enums.Role import Role, is_legacy_admin_role_value
from Enums import Audience
from Enums.UserState import UserState

from framework.Nodes.CallbackNode import CallbackNode
from framework.RecipientLanguage import recipient_language_context

from framework.Services.TelegramService import TelegramService
from framework.Services.TriggerService import TriggerService
from framework.Services.UserStateService import UserStateService

from Utils import PrintUtils
from Utils.CustomExceptions import LastAdminException, RoleChangeTargetNotInTeamException
from features.adminpanel import AdminMenu
from features.roles import RoleAssignment
from Utils import Format

from localization.Translator import t


class AssignRolesCallbackNode(CallbackNode):
    audience = Audience.ADMINS

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

        try:
            await self._dispatch(query, action, args)
        except RoleChangeTargetNotInTeamException:
            await self.telegram_service.edit_callback_message(
                query, t('This user is no longer part of the team.'),
                reply_markup=RoleAssignment.build_home_markup())
        except LastAdminException:
            await self.telegram_service.edit_callback_message(
                query, t('Cannot remove the last admin - make someone else an admin first.'),
                reply_markup=RoleAssignment.build_home_markup())

    async def _dispatch(self, query, action: str, args: list[str]):
        match action:
            case RoleAssignment.HOME:
                await self._show_overview(query)
            case RoleAssignment.LIST_ADMINS:
                await self._show_admin_list(query)
            case RoleAssignment.LIST_USERS if is_legacy_admin_role_value(args[0]):
                # A pre-refactor button minted when ADMIN was still a role.
                await self._show_admin_list(query)
            case RoleAssignment.LIST_USERS:
                await self._show_user_list(query, Role(int(args[0])))
            case RoleAssignment.SELECT_USER:
                origin = args[1] if len(args) > 1 else None
                await self._show_assign_options(query, args[0], origin)
            case RoleAssignment.TOGGLE_ADMIN:
                await self._toggle_admin(query, args[0])
            case RoleAssignment.ASSIGN if is_legacy_admin_role_value(args[1]):
                # Old 'make ADMIN' button: an idempotent grant, never a demotion.
                await self._grant_admin(query, args[0])
            case RoleAssignment.ASSIGN:
                await self._assign_role(query, args[0], Role(int(args[1])))

    async def _show_overview(self, query):
        counts, admin_count = self.role_service.overview_counts()
        await self.telegram_service.edit_callback_message(
            query, t('<b>Select a role to manage:</b>'),
            reply_markup=RoleAssignment.build_overview_markup(
                counts, admin_count,
                back_callback_data=AdminMenu.encode(AdminMenu.PANEL)))

    async def _show_user_list(self, query, role: Role):
        await self._show_bucket(
            query, self.role_service.users_with_role(role), origin=str(int(role)),
            header=t('Users with role {role} - tap one to change it:', role=Format.bold(role.name)),
            empty_text=t('No users currently have the role {role}.', role=Format.bold(role.name)))

    async def _show_admin_list(self, query):
        await self._show_bucket(
            query, self.role_service.admins(), origin=RoleAssignment.FROM_ADMIN_LIST,
            header=t('Current admins - tap one to change them:'),
            empty_text=t('No users are currently admins.'))

    async def _show_bucket(self, query, pairs, origin: str, header: str, empty_text: str):
        if len(pairs) == 0:
            await self.telegram_service.edit_callback_message(
                query, empty_text, reply_markup=RoleAssignment.build_home_markup())
            return
        entries = [RoleAssignment.UserListEntry(uts.user_id, PrintUtils.get_player_display_name(user),
                                                uts.role, uts.is_admin)
                   for uts, user in pairs]
        await self.telegram_service.edit_callback_message(
            query, header, reply_markup=RoleAssignment.build_user_list_markup(entries, origin))

    async def _show_assign_options(self, query, user_doc_id: str, origin: str | None):
        user, user_to_state = self.role_service.get_user_and_state(user_doc_id)
        name = Format.bold(PrintUtils.get_player_display_name(user))
        role_label = user_to_state.role.name + (f' {RoleAssignment.ADMIN_MARKER}' if user_to_state.is_admin else '')
        back = RoleAssignment.encode_origin_list(origin, fallback_role=user_to_state.role)
        await self.telegram_service.edit_callback_message(
            query, t('{name} is currently {role}. Assign a new role:',
                     name=name, role=Format.bold(role_label)),
            reply_markup=RoleAssignment.build_assign_markup(user_doc_id, user_to_state.role,
                                                            user_to_state.is_admin, back))

    async def _assign_role(self, query, user_doc_id: str, new_role: Role):
        user, user_to_state = self.role_service.assign_role(user_doc_id, new_role)
        await self._confirm_change(
            query, user, user_to_state,
            user_notice=t('An admin set your role to {role}.', role=Format.bold(new_role.name)),
            confirmation=t('✅ {name} is now {role}.',
                           name=Format.bold(PrintUtils.get_player_display_name(user)),
                           role=Format.bold(new_role.name)))

    async def _toggle_admin(self, query, user_doc_id: str):
        user, user_to_state = self.role_service.toggle_admin(user_doc_id)
        name = Format.bold(PrintUtils.get_player_display_name(user))
        if user_to_state.is_admin:
            notice, confirmation = (t('An admin gave you admin access.'),
                                    t('✅ {name} is now an admin.', name=name))
        else:
            notice, confirmation = (t('An admin removed your admin access.'),
                                    t('✅ {name} is no longer an admin.', name=name))
        await self._confirm_change(query, user, user_to_state, notice, confirmation)

    async def _grant_admin(self, query, user_doc_id: str):
        user, user_to_state, changed = self.role_service.grant_admin(user_doc_id)
        confirmation = t('✅ {name} is now an admin.',
                         name=Format.bold(PrintUtils.get_player_display_name(user)))
        if not changed:
            # Already an admin: nothing to persist or announce.
            await self.telegram_service.edit_callback_message(
                query, confirmation, reply_markup=RoleAssignment.build_home_markup())
            return
        await self._confirm_change(query, user, user_to_state,
                                   user_notice=t('An admin gave you admin access.'),
                                   confirmation=confirmation)

    async def _confirm_change(self, query, user, user_to_state, user_notice: str, confirmation: str):
        notified = await self._notify_user(user, user_to_state, user_notice)
        if not notified:
            confirmation += t('\nCould not notify them - they may have removed Telegram.')
        await self.telegram_service.edit_callback_message(query, confirmation,
                                                          reply_markup=RoleAssignment.build_home_markup())

    async def _notify_user(self, user, user_to_state, message: str) -> bool:
        # Best-effort: the change is already persisted, so a user we can no longer reach
        # (deleted account, blocked bot) must not fail the whole flow.
        default_node = self.node_handler.get_node(UserState.DEFAULT)
        buttons = default_node.get_commands_for_buttons(user_to_state, UserState.DEFAULT)
        try:
            # The notice (and refreshed keyboard) speak the AFFECTED user's language,
            # not the acting admin's.
            with recipient_language_context(self.data_access, user.telegramId):
                await self.telegram_service.send_message(
                    update=user,
                    all_buttons=buttons,
                    message=message)
            return True
        except TelegramError as e:
            logging.info(f'Could not notify user {user.telegramId} of role change: {e}')
            return False
