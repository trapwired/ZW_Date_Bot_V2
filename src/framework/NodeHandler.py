import logging

import telegram
from telegram import Update
from telegram.error import BadRequest
from telegram.constants import ChatType
from telegram.ext import ContextTypes, BaseHandler, CallbackContext

from Enums.UserState import UserState
from Enums.RoleSet import RoleSet

from features.attendance.IcsService import IcsService
from framework.Services.UserStateService import UserStateService
from framework.Services.TelegramService import TelegramService
from framework.Services.TriggerService import TriggerService
from features.eventmgmt.EventService import EventService
from features.attendance.AttendanceService import AttendanceService
from features.roles.RoleService import RoleService
from features.website.WebsiteService import WebsiteService
from features.stats.StatisticsService import StatisticsService

from features.menu.DefaultNode import DefaultNode
from features.onboarding.InitNode import InitNode
from features.onboarding.RejectedNode import RejectedNode
from features.eventmgmt.AddEventFieldsNode import AddEventFieldsNode
from features.eventmgmt.EditEventFieldNode import EditEventFieldNode
from features.website.UpdateWebsiteNode import UpdateWebsiteNode

from features.events import EventsMenu
from features.events.EventsView import EventsView
from features.events.EventsCallbackNode import EventsCallbackNode
from features.adminpanel import AdminMenu
from features.adminpanel.AdminMenuCallbackNode import AdminMenuCallbackNode
from features.roles import RoleAssignment
from features.roles.AssignRolesCallbackNode import AssignRolesCallbackNode

from data.DataAccess import DataAccess

from Utils.CustomExceptions import NodesMissingException, ObjectNotFoundException, MissingCommandDescriptionException
from framework.CommandDescriptions import CommandDescriptions
from Utils.ApiConfig import ApiConfig

EXPIRED_MENU_TEXT = ('This menu is from an older version of the bot and no longer works - '
                     'use the keyboard below (Events / Admin) instead.')


def add_nodes_reference_to_all_nodes(nodes: dict):
    for node in nodes.values():
        node.add_nodes(nodes)


def check_all_user_states_have_node(nodes: dict):
    missing_states = []
    for state in UserState:
        if state not in nodes:
            missing_states.append(state)
    if len(missing_states) > 0:
        raise NodesMissingException(missing_states)


def check_all_commands_have_description(nodes: dict):
    missing_commands = []
    command_set = set()
    for node in nodes.values():
        for transition in node.transitions:
            if transition.needs_description:
                command_set.add(transition.command)

    descriptions = CommandDescriptions.descriptions
    for command in command_set:
        if command not in descriptions:
            missing_commands.append(command)

    if len(missing_commands) > 0:
        raise MissingCommandDescriptionException(missing_commands)


class NodeHandler(BaseHandler[Update, CallbackContext, None]):
    GROUP_TYPES = [ChatType.GROUP, ChatType.SUPERGROUP]

    def __init__(self, bot: telegram.Bot, api_config: ApiConfig, telegram_service: TelegramService,
                 user_state_service: UserStateService, ics_service: IcsService,
                 data_access: DataAccess, trigger_service: TriggerService, event_service: EventService,
                 attendance_service: AttendanceService, role_service: RoleService, website_service: WebsiteService,
                 statistics_service: StatisticsService):
        super().__init__(self.handle_message)
        self.bot = bot
        self.user_state_service = user_state_service
        self.data_access = data_access
        self.telegram_service = telegram_service
        self.event_service = event_service
        self.attendance_service = attendance_service
        self.role_service = role_service
        self.website_service = website_service
        self.statistics_service = statistics_service

        self.events_view = EventsView(event_service, attendance_service, statistics_service)

        self.nodes = self.initialize_nodes(telegram_service, user_state_service, data_access, api_config)
        self.initialize_callback_nodes(telegram_service, data_access, trigger_service, ics_service,
                                       user_state_service)
        add_nodes_reference_to_all_nodes(self.nodes)

        self.do_checks(api_config)

    def check_update(self, update: object):
        if isinstance(update, Update):
            return True
        return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if update.effective_chat is None:
                # Chat-less updates (e.g. poll answers) have no state to route; ignore them.
                return
            # Log a compact, non-PII summary rather than the full Update (which carries names).
            logging.info('Update: chat_type=%s, callback=%s',
                         update.effective_chat.type, update.callback_query is not None)
            chat_type = update.effective_chat.type

            if chat_type in self.GROUP_TYPES:
                # Handle group messages
                return

            if update.callback_query:
                callback_node = self.get_callback_node(update.callback_query.data)
                if callback_node is None:
                    # A button from a retired menu (pre-redesign message): degrade
                    # gracefully instead of alerting the maintainer.
                    await update.callback_query.answer()
                    await self.telegram_service.edit_callback_message(update.callback_query, EXPIRED_MENU_TEXT)
                    return
                if not self.is_caller_allowed(update, callback_node):
                    # Forwarded inline buttons keep working callback_data; gate admin actions
                    # by the pressing user's role, mirroring Transition.allowed_roles for text.
                    await update.callback_query.answer()
                    return
                await callback_node.handle(update)
                return

            if not update.message or not update.message.text:
                # Handle pictures and else
                return

            users_to_state, node = self.get_user_state_and_node(update)
            await node.handle(update, users_to_state)
        except BadRequest as e:
            if "Message is not modified" in str(e):
                logging.debug(f"Ignoring 'Message is not modified' error: {e}")
                return
            await self.telegram_service.report_exception('Exception in NodeHandler.handle_message', e, update)
        except Exception as e:
            await self.telegram_service.report_exception('Exception in NodeHandler.handle_message', e, update)

    def get_user_state_and_node(self, update):
        telegram_id = update.effective_chat.id
        try:
            users_to_state = self.user_state_service.get_user_state(telegram_id)
            user_state = users_to_state.state
        except ObjectNotFoundException:
            users_to_state = None
            user_state = UserState.INIT

        node = self.nodes[user_state]
        return users_to_state, node

    def initialize_nodes(self, telegram_service: TelegramService, user_state_service: UserStateService,
                         data_access: DataAccess, api_config: ApiConfig):

        init_node = InitNode(UserState.INIT, telegram_service, user_state_service, data_access, api_config, self.bot)
        init_node.add_transition('/start', init_node.handle_start, allowed_roles=RoleSet.REALLY_EVERYONE)

        rejected_node = RejectedNode(UserState.INIT, telegram_service, user_state_service, data_access)
        rejected_node.add_transition(
            api_config.get_key('Chats', 'SPECTATOR_PASSWORD'),
            rejected_node.handle_correct_password,
            new_state=UserState.DEFAULT,
            allowed_roles=RoleSet.REJECTED,
            needs_description=False,
            in_keyboard=False)

        default_node = DefaultNode(UserState.DEFAULT, telegram_service, user_state_service, data_access,
                                   self.website_service, self.events_view)
        default_node.add_transition('events', default_node.handle_events)
        default_node.add_transition('admin', default_node.handle_admin, allowed_roles=RoleSet.ADMINS)
        default_node.add_transition('website', default_node.handle_website)
        default_node.add_transition('/privacy', default_node.handle_privacy, allowed_roles=RoleSet.REALLY_EVERYONE,
                                    in_keyboard=False)

        add_event_node = AddEventFieldsNode(UserState.ADMIN_ADD_EVENT, telegram_service, user_state_service,
                                            data_access, self.event_service)

        edit_event_field_node = EditEventFieldNode(UserState.ADMIN_UPDATE_EVENT_FIELD, telegram_service,
                                                   user_state_service, data_access, self.event_service,
                                                   self.events_view)

        update_website_node = UpdateWebsiteNode(UserState.ADMIN_UPDATE_WEBSITE, telegram_service, user_state_service,
                                                data_access, self.website_service)

        return {
            UserState.INIT: init_node,
            UserState.REJECTED: rejected_node,
            UserState.DEFAULT: default_node,
            UserState.ADMIN_ADD_EVENT: add_event_node,
            UserState.ADMIN_UPDATE_EVENT_FIELD: edit_event_field_node,
            UserState.ADMIN_UPDATE_WEBSITE: update_website_node,
        }

    def initialize_callback_nodes(self, telegram_service: TelegramService, data_access: DataAccess,
                                  trigger_service: TriggerService, ics_service: IcsService,
                                  user_state_service: UserStateService):
        self.events_callback_node = EventsCallbackNode(
            telegram_service, data_access, trigger_service, user_state_service, ics_service,
            self.attendance_service, self.event_service, self.events_view)
        self.admin_menu_callback_node = AdminMenuCallbackNode(
            telegram_service, data_access, trigger_service, user_state_service, self.statistics_service,
            self.website_service, self.event_service, self.nodes[UserState.ADMIN_ADD_EVENT])
        self.assign_roles_callback_node = AssignRolesCallbackNode(
            telegram_service, data_access, trigger_service, user_state_service, self, self.role_service)

    def do_checks(self, api_config: ApiConfig):
        check_all_user_states_have_node(self.nodes)
        check_all_commands_have_description(self.nodes)

    def is_caller_allowed(self, update, callback_node) -> bool:
        try:
            role = self.user_state_service.get_user_state(update.effective_chat.id).role
        except ObjectNotFoundException:
            return False
        return role in callback_node.required_roles

    def get_callback_node(self, callback_data: str):
        """Route a callback press to its slice's node by data prefix; None means the
        button belongs to no current menu (a pre-redesign message)."""
        if RoleAssignment.is_role_callback(callback_data):
            return self.assign_roles_callback_node
        if EventsMenu.is_events_callback(callback_data) or EventsMenu.is_legacy_attendance_callback(callback_data):
            return self.events_callback_node
        if AdminMenu.is_admin_menu_callback(callback_data):
            return self.admin_menu_callback_node
        return None

    def get_node(self, user_state: UserState):
        return self.nodes[user_state]
