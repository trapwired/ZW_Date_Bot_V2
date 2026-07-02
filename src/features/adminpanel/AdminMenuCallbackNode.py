from telegram import Update

from framework.Nodes.CallbackNode import CallbackNode

from Enums.EventField import EventField
from Enums.Event import Event
from Enums.RoleSet import RoleSet
from Enums.UserState import UserState

from data.DataAccess import DataAccess

from framework.Services.TelegramService import TelegramService
from framework.Services.TriggerService import TriggerService
from framework.Services.UserStateService import UserStateService

from features.adminpanel import AdminMenu

from Utils import PrintUtils
from Utils.CustomExceptions import NoTempDataFoundException

RESET_CONFIRM_TEXT = ('Are you sure you want to end the current season?\n\n'
                      'This permanently resets the reminder statistics for ALL players and cannot be undone.')


class AdminMenuCallbackNode(CallbackNode):
    """Handles every press inside the admin menu. Navigation happens by editing the one
    menu message in place; only the add-event wizard and the website update hand over
    to a typed-input state."""

    required_roles = RoleSet.ADMINS

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 user_state_service: UserStateService, statistics_service, website_service, event_service,
                 add_event_node):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service
        self.statistics_service = statistics_service
        self.website_service = website_service
        self.event_service = event_service
        self.add_event_node = add_event_node

    async def handle(self, update: Update):
        query = update.callback_query
        parsed = AdminMenu.parse(query.data)
        if parsed is None:
            await query.answer()
            return
        action, args = parsed

        match action:
            case AdminMenu.PANEL:
                await self._show_panel(update, query)
            case AdminMenu.ADD_CHOOSER if len(args) == 0:
                await self._show_add_chooser(query)
            case AdminMenu.ADD_CHOOSER:
                await self._start_add_wizard(update, query, Event(int(args[0])))
            case AdminMenu.STATS_MENU if len(args) == 0:
                await self._show_stats_menu(query)
            case AdminMenu.STATS_MENU:
                await self._show_statistics(query, args[0])
            case AdminMenu.RESET_CONFIRM:
                await self._edit(query, RESET_CONFIRM_TEXT, AdminMenu.build_reset_confirm_markup())
            case AdminMenu.RESET_CONFIRMED:
                await self._reset_statistics(query)
            case AdminMenu.WEBSITE_PROMPT:
                await self._prompt_website(update, query)
            case AdminMenu.WEBSITE_YES | AdminMenu.WEBSITE_NO:
                await self._finish_website(update, query, action)
            case AdminMenu.WIZARD_CANCEL | AdminMenu.WIZARD_RESTART | AdminMenu.WIZARD_SAVE:
                await self._handle_wizard_action(update, query, action)
            case _:
                await query.answer()

    ##############
    # NAVIGATION #
    ##############

    async def _show_panel(self, update: Update, query):
        # Back-to-menu is also the escape hatch out of a typed-input flow (website URL,
        # field value, wizard): whatever was staged is dropped so the next text isn't
        # misread - same cleanup the typed keyboard escapes run.
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        if user_to_state.state is not UserState.DEFAULT:
            if user_to_state.state is UserState.ADMIN_ADD_EVENT:
                self.event_service.discard_draft_if_any(user_to_state.user_id)
            user_to_state.additional_info = ''
            self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self._edit(query, AdminMenu.PANEL_TEXT, AdminMenu.build_panel_markup())

    async def _show_add_chooser(self, query):
        await self._edit(query, 'What kind of event do you want to add?', AdminMenu.build_add_chooser_markup())

    async def _show_stats_menu(self, query):
        await self._edit(query, 'Which statistics do you want to see?', AdminMenu.build_stats_menu_markup())

    ##############
    # STATISTICS #
    ##############

    async def _show_statistics(self, query, stats_code: str):
        if stats_code == AdminMenu.REMINDER_STATISTICS:
            message = PrintUtils.pretty_print_statistics(self.statistics_service.get_player_reminder_metrics())
        else:
            event_type = Event(int(stats_code))
            statistics = self.statistics_service.get_attendance_statistics(event_type)
            message = PrintUtils.pretty_print_event_statistics(statistics, event_type)
        await self._edit(query, message, AdminMenu.build_back_to_stats_markup())

    async def _reset_statistics(self, query):
        deleted_count = self.statistics_service.reset_reminder_statistics()
        message = (f'Done - the season has ended. Reminder statistics were reset for all '
                   f'players ({deleted_count} entries removed).')
        await self._edit(query, message, AdminMenu.build_back_to_stats_markup())

    ###########
    # WEBSITE #
    ###########

    async def _prompt_website(self, update: Update, query):
        current = self.website_service.get_url()
        current_text = current if current else 'not set'
        message = (f'The website link shown to players is currently:\n{current_text}\n\n'
                   'Send me the new URL, or /cancel to abort.')

        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN_UPDATE_WEBSITE)
        await self._edit(query, message)

    async def _finish_website(self, update: Update, query, action: str):
        telegram_id = update.effective_chat.id
        if action == AdminMenu.WEBSITE_YES:
            new_url, user_to_state = self.website_service.commit_pending_url(telegram_id)
            if new_url is None:
                message = ('⚠️ That doesn\'t look like a valid URL - it must start with http:// or https://.\n'
                           'The website link was not changed.')
            else:
                message = f'✅ The website link was updated to:\n{new_url}'
        else:
            user_to_state = self.website_service.discard_pending_url(telegram_id)
            message = 'Cancelled - the website link was not changed.'

        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self._edit(query, message)

    ####################
    # ADD-EVENT WIZARD #
    ####################

    async def _start_add_wizard(self, update: Update, query, event_type: Event):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        temp_data = self.event_service.create_draft(user_to_state.user_id, event_type)
        # The menu message becomes the draft display the wizard keeps updating.
        temp_data.add_inline_information(query.message.chat_id, query.message.id)
        self.event_service.save_draft(temp_data)
        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN_ADD_EVENT)

        # Rendered by the wizard node so the first draft display and every re-render
        # after a typed step come from the same code path.
        await query.answer()
        await self.add_event_node.update_inline_message(temp_data, 'Adding new', can_save=False)
        prompt = PrintUtils.get_update_attribute_message(EventField.DATETIME)
        await self.telegram_service.send_message(update=update, all_buttons=None, message=prompt)

    async def _handle_wizard_action(self, update: Update, query, action: str):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        try:
            temp_data = self.event_service.get_draft(user_to_state.user_id)
        except NoTempDataFoundException:
            # Stale button: the draft was already saved or discarded.
            await self._edit(query, 'This draft is no longer active - start again via the admin menu.')
            return

        match action:
            case AdminMenu.WIZARD_CANCEL:
                self.event_service.discard_draft(temp_data)
                self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
                await self._edit(query, 'Cancelled - the event was not saved.')
            case AdminMenu.WIZARD_RESTART:
                # Discard first: the wizard looks drafts up by user, so the old one must
                # be gone before the fresh one exists.
                self.event_service.discard_draft(temp_data)
                await self._start_add_wizard(update, query, temp_data.event_type)
            case AdminMenu.WIZARD_SAVE:
                await query.answer()
                await self.add_event_node.handle_save(update, user_to_state, temp_data)

    async def _edit(self, query, message: str, reply_markup=None):
        await query.answer()
        await self.telegram_service.edit_callback_message(query, message, reply_markup)
