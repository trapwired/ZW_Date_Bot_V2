import logging

import telegram
from telegram import Update
from telegram.error import BadRequest
from telegram.constants import ChatType
from telegram.ext import ContextTypes, BaseHandler, CallbackContext

from Enums.UserState import UserState
from Enums import Audience

from features.attendance.IcsService import IcsService
from framework.Services.UserStateService import UserStateService
from framework.Services.TelegramService import TelegramService
from framework.Services.TeamService import TeamService
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
from features.teams import TeamRegistration as team_registration_command
from features.teams.TeamRegistration import TeamRegistration
from features.teams.UpdateSpectatorPasswordNode import UpdateSpectatorPasswordNode
from features.teams.UpdateTeamNameNode import UpdateTeamNameNode
from features.onboarding import OnboardingMenu
from features.onboarding.OnboardingCallbackNode import OnboardingCallbackNode
from features.website.UpdateWebsiteNode import UpdateWebsiteNode
from features.announce.AnnounceNode import AnnounceNode
from features.announce.AnnounceService import AnnounceService

from features.events import EventsMenu
from features.events.EventsView import EventsView
from features.events.EventsCallbackNode import EventsCallbackNode
from features.adminpanel import AdminMenu
from features.adminpanel.AdminMenuCallbackNode import AdminMenuCallbackNode
from features.roles import RoleAssignment
from features.roles.AssignRolesCallbackNode import AssignRolesCallbackNode
from features.language import LanguageMenu
from features.language.LanguageCallbackNode import LanguageCallbackNode

from domain.entities.UsersToState import UsersToState

from data.DataAccess import DataAccess
from data.TenantContext import set_current_team, reset_current_team

from localization.LanguageContext import set_current_language, reset_current_language
from localization.Languages import resolve_user_language, normalize as normalize_language
from localization.Translator import t

from Utils.CustomExceptions import NodesMissingException, ObjectNotFoundException, MissingCommandDescriptionException
from framework import TeamStamp
from framework.CommandDescriptions import CommandDescriptions
from Utils.ApiConfig import ApiConfig

EXPIRED_MENU_TEXT = ('This menu is from an older version of the bot and no longer works - '
                     'use the keyboard below (Events / Admin) instead.')
FOREIGN_TEAM_MENU_TEXT = 'This menu belongs to a different team.'


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
                 statistics_service: StatisticsService, team_service: TeamService):
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
        self.team_service = team_service
        self.team_registration = TeamRegistration(bot, telegram_service, user_state_service, team_service,
                                                  data_access, self)

        self.events_view = EventsView(event_service, attendance_service, statistics_service)

        self.nodes = self.initialize_nodes(telegram_service, user_state_service, data_access, api_config)
        self.initialize_callback_nodes(telegram_service, data_access, trigger_service, ics_service,
                                       user_state_service)
        add_nodes_reference_to_all_nodes(self.nodes)
        # /language works from every state, like /help - registered centrally so a new
        # node can't forget it. Roles without a stored profile (INIT) can't persist a
        # choice, so EVERYONE (the default) is the right gate.
        for node in self.nodes.values():
            node.add_transition('/language', self.language_callback_node.send_picker, in_keyboard=False)

        self.do_checks(api_config)

    def check_update(self, update: object):
        if isinstance(update, Update):
            return True
        return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context_token = None
        language_token = None
        try:
            if update.effective_chat is None:
                # Chat-less updates (e.g. poll answers) have no state to route; ignore them.
                return
            # Log a compact, non-PII summary rather than the full Update (which carries names).
            logging.info('Update: chat_type=%s, callback=%s',
                         update.effective_chat.type, update.callback_query is not None)
            chat_type = update.effective_chat.type

            if update.my_chat_member:
                # The bot's own membership changed (added to / removed from a chat) -
                # the team-lifecycle trigger for guided onboarding. No user state here;
                # the acting user's client language decides.
                language_token = self._set_language(None, update)
                await self.team_registration.handle_my_chat_member(update)
                return

            if chat_type in self.GROUP_TYPES:
                # Groups are ignored except for the one command that claims a group as a team.
                if team_registration_command.is_register_team_command(update):
                    language_token = self._set_language(None, update)
                    await self.team_registration.handle(update)
                return

            if update.callback_query:
                users_to_state, context_token = self._resolve_tenant(update.effective_chat.id)
                language_token = self._set_language(users_to_state, update)
                callback_node = self.get_callback_node(update.callback_query.data)
                if callback_node is None:
                    # A button from a retired menu (pre-redesign message): degrade
                    # gracefully instead of alerting the maintainer.
                    await update.callback_query.answer()
                    await self.telegram_service.edit_callback_message(update.callback_query, t(EXPIRED_MENU_TEXT))
                    return
                if not self.is_caller_allowed(users_to_state, callback_node):
                    await update.callback_query.answer()
                    return
                stamped_team = TeamStamp.stamped_team(update.callback_query.data)
                if stamped_team is not None and stamped_team != users_to_state.team_id:
                    # A forwarded button from another team's menu: acting would write
                    # foreign ids into the presser's team. Unstamped (pre-stamp) buttons
                    # pass - they lose nothing they had.
                    await update.callback_query.answer()
                    await self.telegram_service.edit_callback_message(
                        update.callback_query, t(FOREIGN_TEAM_MENU_TEXT))
                    return
                await callback_node.handle(update)
                return

            if not update.message or not update.message.text:
                # Handle pictures and else
                return

            users_to_state, context_token = self._resolve_tenant(update.effective_chat.id)
            language_token = self._set_language(users_to_state, update)
            node = self.nodes[users_to_state.state] if users_to_state else self.nodes[UserState.INIT]
            await node.handle(update, users_to_state)
        except BadRequest as e:
            if "Message is not modified" in str(e):
                logging.debug(f"Ignoring 'Message is not modified' error: {e}")
                return
            await self.telegram_service.report_exception('Exception in NodeHandler.handle_message', e, update)
        except Exception as e:
            await self.telegram_service.report_exception('Exception in NodeHandler.handle_message', e, update)
        finally:
            if context_token is not None:
                reset_current_team(context_token)
            if language_token is not None:
                reset_current_language(language_token)

    def _resolve_tenant(self, telegram_id) -> tuple[UsersToState | None, object]:
        """The one user-state read per update, plus the tenant-context switch derived
        from it. INIT/REJECTED users have no team and only ever touch global
        collections - any accidental domain read fails closed."""
        try:
            users_to_state = self.user_state_service.get_user_state(telegram_id)
        except ObjectNotFoundException:
            users_to_state = None
        token = set_current_team(users_to_state.team_id if users_to_state else None)
        return users_to_state, token

    def _set_language(self, users_to_state: UsersToState | None, update: Update):
        """The ambient language for this update: the user's saved /language choice,
        else their Telegram client language, else English (fail-open).

        First contact snapshots the client language into the profile (one write per
        user, ever): fan-out sends (reminders, announcements) run outside any update
        and can only read the stored value. /language overrides it at any time."""
        saved = users_to_state.language if users_to_state else None
        # getattr: test doubles (and some update types) carry no language_code - fail open.
        client_code = getattr(update.effective_user, 'language_code', None) if update.effective_user else None
        if users_to_state is not None and saved is None:
            derived = normalize_language(client_code)
            if derived is not None:
                self.user_state_service.set_language(users_to_state, derived)
        return set_current_language(resolve_user_language(saved, client_code))

    def initialize_nodes(self, telegram_service: TelegramService, user_state_service: UserStateService,
                         data_access: DataAccess, api_config: ApiConfig):

        init_node = InitNode(UserState.INIT, telegram_service, user_state_service, data_access, self.bot,
                             self.team_service)
        init_node.add_transition('/start', init_node.handle_start, audience=Audience.REALLY_EVERYONE)

        # Any unmatched text on the REJECTED node is treated as a spectator-password
        # attempt (RejectedNode.fallback_action); the password identifies the team.
        rejected_node = RejectedNode(UserState.REJECTED, telegram_service, user_state_service, data_access,
                                     self.team_service)

        default_node = DefaultNode(UserState.DEFAULT, telegram_service, user_state_service, data_access,
                                   self.website_service, self.events_view, self.team_service)
        default_node.add_transition('events', default_node.handle_events)
        default_node.add_transition('admin', default_node.handle_admin, audience=Audience.ADMINS)
        default_node.add_transition('website', default_node.handle_website)
        default_node.add_transition('/privacy', default_node.handle_privacy, audience=Audience.REALLY_EVERYONE,
                                    in_keyboard=False)

        add_event_node = AddEventFieldsNode(UserState.ADMIN_ADD_EVENT, telegram_service, user_state_service,
                                            data_access, self.event_service)

        edit_event_field_node = EditEventFieldNode(UserState.ADMIN_UPDATE_EVENT_FIELD, telegram_service,
                                                   user_state_service, data_access, self.event_service,
                                                   self.events_view)

        update_website_node = UpdateWebsiteNode(UserState.ADMIN_UPDATE_WEBSITE, telegram_service,
                                                user_state_service, data_access)

        update_spectator_password_node = UpdateSpectatorPasswordNode(
            UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD, telegram_service, user_state_service, data_access)

        announce_node = AnnounceNode(UserState.ADMIN_ANNOUNCE, telegram_service, user_state_service, data_access)

        update_team_name_node = UpdateTeamNameNode(UserState.ADMIN_UPDATE_TEAM_NAME, telegram_service,
                                                   user_state_service, data_access)

        return {
            UserState.INIT: init_node,
            UserState.REJECTED: rejected_node,
            UserState.DEFAULT: default_node,
            UserState.ADMIN_ADD_EVENT: add_event_node,
            UserState.ADMIN_UPDATE_EVENT_FIELD: edit_event_field_node,
            UserState.ADMIN_UPDATE_WEBSITE: update_website_node,
            UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD: update_spectator_password_node,
            UserState.ADMIN_ANNOUNCE: announce_node,
            UserState.ADMIN_UPDATE_TEAM_NAME: update_team_name_node,
        }

    def initialize_callback_nodes(self, telegram_service: TelegramService, data_access: DataAccess,
                                  trigger_service: TriggerService, ics_service: IcsService,
                                  user_state_service: UserStateService):
        self.events_callback_node = EventsCallbackNode(
            telegram_service, data_access, trigger_service, user_state_service, ics_service,
            self.attendance_service, self.event_service, self.events_view)
        self.admin_menu_callback_node = AdminMenuCallbackNode(
            telegram_service, data_access, trigger_service, user_state_service, self.statistics_service,
            self.website_service, self.event_service, self.nodes[UserState.ADMIN_ADD_EVENT], self.team_service,
            AnnounceService(data_access, telegram_service))
        self.assign_roles_callback_node = AssignRolesCallbackNode(
            telegram_service, data_access, trigger_service, user_state_service, self, self.role_service)
        self.onboarding_callback_node = OnboardingCallbackNode(telegram_service, data_access, trigger_service,
                                                                user_state_service)
        self.language_callback_node = LanguageCallbackNode(telegram_service, data_access, trigger_service,
                                                           user_state_service, self)

    def do_checks(self, api_config: ApiConfig):
        check_all_user_states_have_node(self.nodes)
        check_all_commands_have_description(self.nodes)

    def is_caller_allowed(self, users_to_state, callback_node) -> bool:
        # Forwarded inline buttons keep working callback_data; an unregistered presser
        # (no state) is never allowed, and otherwise gate by the pressing user's role.
        return users_to_state is not None and callback_node.audience.allows(users_to_state)

    def get_callback_node(self, callback_data: str):
        """Route a callback press to its slice's node by data prefix; None means the
        button belongs to no current menu (a pre-redesign message)."""
        if RoleAssignment.is_role_callback(callback_data):
            return self.assign_roles_callback_node
        if EventsMenu.is_events_callback(callback_data) or EventsMenu.is_legacy_attendance_callback(callback_data):
            return self.events_callback_node
        if AdminMenu.is_admin_menu_callback(callback_data):
            return self.admin_menu_callback_node
        if OnboardingMenu.is_onboarding_callback(callback_data):
            return self.onboarding_callback_node
        if LanguageMenu.is_language_callback(callback_data):
            return self.language_callback_node
        return None

    def get_node(self, user_state: UserState):
        return self.nodes[user_state]
