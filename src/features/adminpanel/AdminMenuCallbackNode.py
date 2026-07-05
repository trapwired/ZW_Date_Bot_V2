from telegram import Update
from telegram.error import TelegramError

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

from Utils import Format
from Utils import InlineInputStaging
from Utils import PrintUtils
from Utils.CustomExceptions import NoTempDataFoundException, \
    SpectatorPasswordAlreadyTakenException, SpectatorPasswordNotAllowedException

RESET_CONFIRM_TEXT = ('Are you sure you want to end the current season?\n\n'
                      'This permanently resets the reminder statistics for ALL players and cannot be undone.')


class AdminMenuCallbackNode(CallbackNode):
    """Handles every press inside the admin menu. Navigation happens by editing the one
    menu message in place; only the add-event wizard and the website update hand over
    to a typed-input state."""

    required_roles = RoleSet.ADMINS

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 user_state_service: UserStateService, statistics_service, website_service, event_service,
                 add_event_node, team_service, announce_service):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service
        self.statistics_service = statistics_service
        self.website_service = website_service
        self.event_service = event_service
        self.add_event_node = add_event_node
        self.team_service = team_service
        self.announce_service = announce_service

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
            case AdminMenu.SPECTATOR_PASSWORD_PROMPT:
                await self._prompt_spectator_password(update, query)
            case AdminMenu.SPECTATOR_PASSWORD_SAVE | AdminMenu.SPECTATOR_PASSWORD_CANCEL:
                await self._finish_spectator_password(update, query, action)
            case AdminMenu.TEAM_NAME_PROMPT:
                await self._prompt_team_name(update, query)
            case AdminMenu.TEAM_NAME_SAVE | AdminMenu.TEAM_NAME_CANCEL:
                await self._finish_team_name(update, query, action)
            case AdminMenu.ANNOUNCE_PROMPT:
                await self._prompt_announcement(update, query)
            case AdminMenu.ANNOUNCE_TO_PLAYERS | AdminMenu.ANNOUNCE_TO_GROUP:
                await self._finish_announcement(update, query, action)
            case AdminMenu.TRAINERS_MENU:
                await self._show_trainers_menu(query)
            case AdminMenu.TRAINERS_LIST if len(args) == 1:
                await self._show_trainer_list(query, Event(int(args[0])))
            case AdminMenu.TRAINERS_TOGGLE if len(args) == 2:
                await self._toggle_trainer(query, Event(int(args[0])), int(args[1]))
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
                await self.add_event_node.abort_draft(user_to_state)
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

    ###############
    # TYPED INPUT #
    ###############

    async def _start_typed_input(self, update: Update, query, target_state: UserState, prompt: str):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        # Remember which menu message to keep re-rendering while the admin types;
        # nothing is persisted or sent until they confirm.
        user_to_state.additional_info = InlineInputStaging.build(
            query.message.message_id, query.message.chat.id, '')
        self.user_state_service.update_user_state(user_to_state, target_state)
        await self._edit(query, prompt, AdminMenu.build_typed_input_prompt_markup())

    async def _finish_typed_input(self, query, user_to_state, confirmation: str):
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self._edit(query, confirmation, AdminMenu.build_back_to_panel_markup())

    ###########
    # WEBSITE #
    ###########

    async def _prompt_website(self, update: Update, query):
        current = self.website_service.get_url()
        current_text = Format.escape(current) if current else 'not set'
        message = (f'The website link shown to players is currently:\n{current_text}\n\n'
                   'Send me the new URL.')
        await self._start_typed_input(update, query, UserState.ADMIN_UPDATE_WEBSITE, message)

    async def _finish_website(self, update: Update, query, action: str):
        telegram_id = update.effective_chat.id
        if action == AdminMenu.WEBSITE_NO:
            user_to_state = self.website_service.discard_pending_url(telegram_id)
            self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
            await self._show_panel(update, query)
            return

        new_url, user_to_state = self.website_service.commit_pending_url(telegram_id)
        if new_url is None:
            message = ('⚠️ That doesn\'t look like a valid URL - it must start with http:// or https://.\n'
                       'The website link was not changed.')
        else:
            message = f'✅ The website link was updated to:\n{new_url}'
        await self._finish_typed_input(query, user_to_state, message)

    ######################
    # SPECTATOR PASSWORD #
    ######################

    async def _prompt_spectator_password(self, update: Update, query):
        current = self.team_service.current_team().spectator_password
        current_text = Format.escape(current) if current else 'not set'
        message = (f'The spectator password for this team is currently:\n{current_text}\n\n'
                   'Send me the new password.')
        await self._start_typed_input(update, query, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD, message)

    async def _finish_spectator_password(self, update: Update, query, action: str):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        message_id, chat_id, password = InlineInputStaging.parse(user_to_state.additional_info)

        if action == AdminMenu.SPECTATOR_PASSWORD_CANCEL:
            user_to_state.additional_info = ''
            self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
            await self._show_panel(update, query)
            return

        try:
            self.team_service.set_spectator_password(self.team_service.current_team(), password)
        except SpectatorPasswordNotAllowedException:
            await self._reprompt_password(query, user_to_state, message_id, chat_id,
                                          '⚠️ That password cannot be used (at least 6 characters, no help commands) - '
                                          'send me a different one.')
            return
        except SpectatorPasswordAlreadyTakenException:
            await self._reprompt_password(query, user_to_state, message_id, chat_id,
                                          '⚠️ Another team already uses that password - send me a different one.')
            return

        await self._finish_typed_input(query, user_to_state, '✅ The spectator password was updated.')

    async def _reprompt_password(self, query, user_to_state, message_id, chat_id, message: str):
        # A rejected password shouldn't cost the admin the whole flow: stay in the
        # typed-input state so the next message is simply another attempt.
        user_to_state.additional_info = InlineInputStaging.build(message_id, chat_id, '')
        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD)
        await self._edit(query, message, AdminMenu.build_typed_input_prompt_markup())

    #############
    # TEAM NAME #
    #############

    async def _prompt_team_name(self, update: Update, query):
        current = Format.escape(self.team_service.current_team().name)
        message = f'The team is currently named:\n{current}\n\nSend me the new name.'
        await self._start_typed_input(update, query, UserState.ADMIN_UPDATE_TEAM_NAME, message)

    async def _finish_team_name(self, update: Update, query, action: str):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        if user_to_state.state is not UserState.ADMIN_UPDATE_TEAM_NAME:
            # Stale button from an abandoned flow: additional_info may hold ANOTHER
            # flow's staged value (a password!) - never commit it as the team name,
            # and never touch that flow's state.
            await self._edit(query, 'This rename is no longer active - start again via the admin menu.',
                             AdminMenu.build_back_to_panel_markup())
            return
        if action == AdminMenu.TEAM_NAME_CANCEL:
            user_to_state.additional_info = ''
            self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
            await self._show_panel(update, query)
            return

        _, _, new_name = InlineInputStaging.parse(user_to_state.additional_info)
        try:
            self.team_service.rename_team(self.team_service.current_team(), new_name)
        except ValueError:
            await self._edit(query, '⚠️ The team name cannot be empty - send me a different one.',
                             AdminMenu.build_typed_input_prompt_markup())
            return
        await self._finish_typed_input(query, user_to_state,
                                       f'✅ The team is now named "{Format.escape(new_name.strip())}".')

    ################
    # ANNOUNCEMENT #
    ################

    async def _prompt_announcement(self, update: Update, query):
        message = ('Send me the announcement text. You will choose afterwards whether it goes '
                   'to every player privately or into the team group chat.')
        await self._start_typed_input(update, query, UserState.ADMIN_ANNOUNCE, message)

    async def _finish_announcement(self, update: Update, query, action: str):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        if user_to_state.state is not UserState.ADMIN_ANNOUNCE:
            # Stale button from an abandoned flow: additional_info may hold ANOTHER
            # flow's staged value (a password, a URL) - never broadcast it, and never
            # touch that flow's state.
            await self._edit(query, 'This announcement is no longer active - start again via the admin menu.',
                             AdminMenu.build_back_to_panel_markup())
            return
        _, _, announcement = InlineInputStaging.parse(user_to_state.additional_info)
        if not announcement:
            # Delivery pressed before any text arrived - keep prompting.
            await self._edit(query, 'There is no announcement text yet - send me the text first.',
                             AdminMenu.build_typed_input_prompt_markup())
            return

        if action == AdminMenu.ANNOUNCE_TO_GROUP:
            try:
                await self.announce_service.send_to_group(announcement)
            except TelegramError:
                # Keep state + staged text so the admin can retry or cancel.
                await self._edit(query, '⚠️ Could not post in the group chat - is the bot still a member? '
                                        'The announcement was not sent.',
                                 AdminMenu.build_typed_input_prompt_markup())
                return
            confirmation = '✅ The announcement was posted in the group chat.'
        else:
            reached = await self.announce_service.send_to_players(announcement)
            confirmation = f'✅ The announcement was sent to {reached} players.'

        await self._finish_typed_input(query, user_to_state, confirmation)

    ############
    # TRAINERS #
    ############

    async def _show_trainers_menu(self, query):
        team = self.team_service.current_team()
        names = dict(self._roster_members())

        def render(trainer_ids: list[int]) -> str:
            if not trainer_ids:
                return Format.italic('group chat (no trainers set)')
            return Format.escape(', '.join(names.get(chat_id, str(chat_id)) for chat_id in trainer_ids))

        message = (Format.bold('Trainers') + '\n'
                   'Attendance summaries and warnings go to the trainers of each event group; '
                   'a group without trainers uses the team group chat instead.\n\n'
                   f'{AdminMenu.TRAINER_GROUP_LABELS[Event.GAME]}: {render(team.trainers_games)}\n'
                   f'{AdminMenu.TRAINER_GROUP_LABELS[Event.TRAINING]}: {render(team.trainers_training)}')
        await self._edit(query, message, AdminMenu.build_trainers_menu_markup())

    async def _show_trainer_list(self, query, event_type: Event):
        trainer_ids = self.team_service.current_team().trainers_for(event_type)
        entries = self._trainer_candidates(trainer_ids)
        message = (f'{AdminMenu.TRAINER_GROUP_LABELS[event_type]} - tap a person to add or remove them '
                   'as trainer. Changes apply immediately.')
        await self._edit(query, message, AdminMenu.build_trainer_toggle_markup(event_type, entries, trainer_ids))

    async def _toggle_trainer(self, query, event_type: Event, chat_id: int):
        self.team_service.toggle_trainer(event_type, chat_id)
        await self._show_trainer_list(query, event_type)

    def _trainer_candidates(self, current_trainer_ids: list[int]) -> list[tuple[int, str]]:
        members = self._roster_members()
        known_ids = {chat_id for chat_id, _ in members}
        # Config-seeded or hand-edited trainer ids without a matching ACTIVE roster
        # member (never /start-ed, retired, ...) stay visible/removable, listed last.
        strays = [(chat_id, f'{chat_id} (not in the roster)')
                  for chat_id in current_trainer_ids if chat_id not in known_ids]
        return members + strays

    def _roster_members(self) -> list[tuple[int, str]]:
        return [(user.telegramId, PrintUtils.get_player_display_name(user))
                for user in PrintUtils.sorted_by_display_name(self.data_access.get_all_players())]

    ####################
    # ADD-EVENT WIZARD #
    ####################

    async def _start_add_wizard(self, update: Update, query, event_type: Event):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        temp_data = self.event_service.create_draft(user_to_state.user_id, event_type)
        # The menu message becomes the draft display the wizard keeps updating.
        temp_data.add_inline_information(query.message.chat_id, query.message.message_id)
        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN_ADD_EVENT)

        # Rendered by the wizard node so the first draft display, the first prompt and
        # every re-render after a typed step come from the same code path.
        await query.answer()
        await self.add_event_node.update_inline_message(temp_data, 'Adding new', can_save=False)
        await self.add_event_node.replace_prompt(update, temp_data, EventField.DATETIME)
        self.event_service.save_draft(temp_data)

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
                await self.add_event_node.abort_draft(user_to_state)
                self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
                await self._edit(query, 'Cancelled - the event was not saved.')
            case AdminMenu.WIZARD_RESTART:
                # Abort first: the wizard looks drafts up by user, so the old one must
                # be gone before the fresh one exists.
                await self.add_event_node.abort_draft(user_to_state)
                await self._start_add_wizard(update, query, temp_data.event_type)
            case AdminMenu.WIZARD_SAVE:
                await query.answer()
                await self.add_event_node.handle_save(update, user_to_state, temp_data)

    async def _edit(self, query, message: str, reply_markup=None):
        await query.answer()
        await self.telegram_service.edit_callback_message(query, message, reply_markup)
