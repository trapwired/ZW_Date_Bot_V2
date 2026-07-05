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

from localization.Languages import NATIVE_NAMES, SUPPORTED_LANGUAGES
from localization.Translator import t

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
                await self._edit(query, t(RESET_CONFIRM_TEXT), AdminMenu.build_reset_confirm_markup())
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
            case AdminMenu.SPECTATORS_MENU:
                await self._show_spectators_menu(update, query)
            case AdminMenu.SETUP_MENU:
                await self._show_setup_menu(update, query)
            case AdminMenu.TEAM_LANGUAGE_MENU:
                await self._show_team_language_menu(update, query)
            case AdminMenu.TEAM_LANGUAGE_SET if len(args) == 1:
                await self._set_team_language(update, query, args[0])
            case AdminMenu.SPECTATOR_INVITE:
                await self._create_spectator_invite(query)
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
        await self._reset_typed_state(update)
        await self._edit(query, t(AdminMenu.PANEL_TEXT), AdminMenu.build_panel_markup())

    async def _reset_typed_state(self, update: Update):
        # Every menu landing is also the escape hatch out of a typed-input flow
        # (website URL, field value, wizard): whatever was staged is dropped so the
        # next text isn't misread - same cleanup the typed keyboard escapes run.
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        if user_to_state.state is not UserState.DEFAULT:
            if user_to_state.state is UserState.ADMIN_ADD_EVENT:
                await self.add_event_node.abort_draft(user_to_state)
            user_to_state.additional_info = ''
            self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)

    async def _show_add_chooser(self, query):
        await self._edit(query, t('What kind of event do you want to add?'), AdminMenu.build_add_chooser_markup())

    async def _show_stats_menu(self, query):
        await self._edit(query, t('Which statistics do you want to see?'), AdminMenu.build_stats_menu_markup())

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
        message = t('Done - the season has ended. Reminder statistics were reset for all '
                    'players ({count} entries removed).', count=deleted_count)
        await self._edit(query, message, AdminMenu.build_back_to_stats_markup())

    ###############
    # TYPED INPUT #
    ###############

    async def _start_typed_input(self, update: Update, query, target_state: UserState, prompt: str,
                                 back_action: str = None):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        # Remember which menu message to keep re-rendering while the admin types;
        # nothing is persisted or sent until they confirm.
        user_to_state.additional_info = InlineInputStaging.build(
            query.message.message_id, query.message.chat.id, '')
        self.user_state_service.update_user_state(user_to_state, target_state)
        await self._edit(query, prompt, AdminMenu.build_typed_input_prompt_markup(back_action))

    async def _finish_typed_input(self, query, user_to_state, confirmation: str, reply_markup=None):
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self._edit(query, confirmation, reply_markup or AdminMenu.build_back_to_panel_markup())

    ###########
    # WEBSITE #
    ###########

    async def _prompt_website(self, update: Update, query):
        current = self.website_service.get_url()
        current_text = Format.escape(current) if current else t('not set')
        message = t('The website link shown to players is currently:\n{current}\n\n'
                    'Send me the new URL.', current=current_text)
        await self._start_typed_input(update, query, UserState.ADMIN_UPDATE_WEBSITE, message,
                                      back_action=AdminMenu.SETUP_MENU)

    async def _finish_website(self, update: Update, query, action: str):
        telegram_id = update.effective_chat.id
        if action == AdminMenu.WEBSITE_NO:
            self.website_service.discard_pending_url(telegram_id)
            await self._show_setup_menu(update, query)
            return

        new_url, user_to_state = self.website_service.commit_pending_url(telegram_id)
        if new_url is None:
            await self._finish_typed_input(
                query, user_to_state,
                t('⚠️ That doesn\'t look like a valid URL - it must start with http:// or https://.\n'
                  'The website link was not changed.'),
                AdminMenu.build_back_markup(AdminMenu.SETUP_MENU))
            return
        # The setup overview shows the committed link - that IS the confirmation.
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self._show_setup_menu(update, query)

    ######################
    # SPECTATOR PASSWORD #
    ######################

    async def _prompt_spectator_password(self, update: Update, query):
        current = self.team_service.current_team().spectator_password
        current_text = Format.escape(current) if current else t('not set')
        message = t('The spectator password for this team is currently:\n{current}\n\n'
                    'Send me the new password.', current=current_text)
        await self._start_typed_input(update, query, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD, message,
                                      back_action=AdminMenu.SPECTATORS_MENU)

    async def _finish_spectator_password(self, update: Update, query, action: str):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        message_id, chat_id, password = InlineInputStaging.parse(user_to_state.additional_info)

        if action == AdminMenu.SPECTATOR_PASSWORD_CANCEL:
            await self._show_spectators_menu(update, query)
            return

        try:
            self.team_service.set_spectator_password(self.team_service.current_team(), password)
        except SpectatorPasswordNotAllowedException:
            await self._reprompt_password(query, user_to_state, message_id, chat_id,
                                          t('⚠️ That password cannot be used (at least 6 characters, no help commands) - '
                                            'send me a different one.'))
            return
        except SpectatorPasswordAlreadyTakenException:
            await self._reprompt_password(query, user_to_state, message_id, chat_id,
                                          t('⚠️ Another team already uses that password - send me a different one.'))
            return

        # The spectators overview shows the new password - that IS the confirmation,
        # and it is where an admin heads next anyway.
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self._show_spectators_menu(update, query)

    async def _reprompt_password(self, query, user_to_state, message_id, chat_id, message: str):
        # A rejected password shouldn't cost the admin the whole flow: stay in the
        # typed-input state so the next message is simply another attempt.
        user_to_state.additional_info = InlineInputStaging.build(message_id, chat_id, '')
        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD)
        await self._edit(query, message, AdminMenu.build_typed_input_prompt_markup(AdminMenu.SPECTATORS_MENU))

    #############
    # TEAM NAME #
    #############

    async def _prompt_team_name(self, update: Update, query):
        current = Format.escape(self.team_service.current_team().name)
        message = t('The team is currently named:\n{current}\n\nSend me the new name.', current=current)
        await self._start_typed_input(update, query, UserState.ADMIN_UPDATE_TEAM_NAME, message,
                                      back_action=AdminMenu.SETUP_MENU)

    async def _finish_team_name(self, update: Update, query, action: str):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        if user_to_state.state is not UserState.ADMIN_UPDATE_TEAM_NAME:
            # Stale button from an abandoned flow: additional_info may hold ANOTHER
            # flow's staged value (a password!) - never commit it as the team name,
            # and never touch that flow's state.
            await self._edit(query, t('This rename is no longer active - start again via the admin menu.'),
                             AdminMenu.build_back_to_panel_markup())
            return
        if action == AdminMenu.TEAM_NAME_CANCEL:
            await self._show_setup_menu(update, query)
            return

        _, _, new_name = InlineInputStaging.parse(user_to_state.additional_info)
        try:
            self.team_service.rename_team(self.team_service.current_team(), new_name)
        except ValueError:
            await self._edit(query, t('⚠️ The team name cannot be empty - send me a different one.'),
                             AdminMenu.build_typed_input_prompt_markup(AdminMenu.SETUP_MENU))
            return
        # The setup overview shows the new name - that IS the confirmation.
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self._show_setup_menu(update, query)

    ##############
    # SPECTATORS #
    ##############

    async def _show_spectators_menu(self, update: Update, query):
        await self._reset_typed_state(update)
        team = self.team_service.current_team()
        password = Format.escape(team.spectator_password) if team.spectator_password \
            else Format.italic(t('not set - nobody can join by password yet'))
        outstanding = len(team.invite_tokens)
        message = t('<b>Spectators</b>\n'
                    'Fans and supporters follow the team read-only. They join with the '
                    'password or a one-time invite link.\n\n'
                    '🔑 Password: {password}\n'
                    '🔗 Outstanding invite links: {outstanding}',
                    password=password, outstanding=outstanding)
        await self._edit(query, message, AdminMenu.build_spectators_menu_markup())

    async def _show_setup_menu(self, update: Update, query):
        await self._reset_typed_state(update)
        team = self.team_service.current_team()
        website = self.website_service.get_url()
        trainer_count = len(set(team.trainers_games) | set(team.trainers_training))
        message = t('<b>Team setup</b>\n\n'
                    '✏️ Name: {name}\n'
                    '🌐 Website: {website}\n'
                    '🧑‍🏫 Trainers: {trainers}\n'
                    '🗣 Language: {language}',
                    name=Format.escape(team.name),
                    website=Format.escape(website) if website else Format.italic(t('not set')),
                    trainers=trainer_count if trainer_count else Format.italic(t('group chat fallback')),
                    language=NATIVE_NAMES.get(team.language, team.language))
        await self._edit(query, message, AdminMenu.build_setup_menu_markup())

    async def _show_team_language_menu(self, update: Update, query):
        await self._reset_typed_state(update)
        team = self.team_service.current_team()
        message = t('Which language should I use in the team group chat and for trainer messages?\n\n'
                    'Every member picks their own language for private chats via /language.')
        await self._edit(query, message, AdminMenu.build_team_language_markup(team.language))

    async def _set_team_language(self, update: Update, query, language: str):
        if language in SUPPORTED_LANGUAGES:
            self.team_service.set_language(self.team_service.current_team(), language)
        # Landing pattern: the setup overview shows the (new) language = the confirmation.
        await self._show_setup_menu(update, query)

    async def _create_spectator_invite(self, query):
        token = self.team_service.create_spectator_invite(self.team_service.current_team())
        username = await self.telegram_service.get_bot_username()
        message = t('Here is a one-time spectator invite - send it to ONE person, it dies '
                    'on first use:\n\n'
                    'https://t.me/{username}?start={token}\n\n'
                    'Generate a new link for each spectator. The spectator password keeps '
                    'working as before.', username=username, token=token)
        await self._edit(query, message, AdminMenu.build_back_markup(AdminMenu.SPECTATORS_MENU))

    ################
    # ANNOUNCEMENT #
    ################

    async def _prompt_announcement(self, update: Update, query):
        message = t('Send me the announcement text. You will choose afterwards whether it goes '
                    'to every player privately or into the team group chat.')
        await self._start_typed_input(update, query, UserState.ADMIN_ANNOUNCE, message)

    async def _finish_announcement(self, update: Update, query, action: str):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        if user_to_state.state is not UserState.ADMIN_ANNOUNCE:
            # Stale button from an abandoned flow: additional_info may hold ANOTHER
            # flow's staged value (a password, a URL) - never broadcast it, and never
            # touch that flow's state.
            await self._edit(query, t('This announcement is no longer active - start again via the admin menu.'),
                             AdminMenu.build_back_to_panel_markup())
            return
        _, _, announcement = InlineInputStaging.parse(user_to_state.additional_info)
        if not announcement:
            # Delivery pressed before any text arrived - keep prompting.
            await self._edit(query, t('There is no announcement text yet - send me the text first.'),
                             AdminMenu.build_typed_input_prompt_markup())
            return

        if action == AdminMenu.ANNOUNCE_TO_GROUP:
            try:
                await self.announce_service.send_to_group(announcement)
            except TelegramError:
                # Keep state + staged text so the admin can retry or cancel.
                await self._edit(query, t('⚠️ Could not post in the group chat - is the bot still a member? '
                                          'The announcement was not sent.'),
                                 AdminMenu.build_typed_input_prompt_markup())
                return
            confirmation = t('✅ The announcement was posted in the group chat.')
        else:
            reached = await self.announce_service.send_to_players(announcement)
            confirmation = t('✅ The announcement was sent to {reached} players.', reached=reached)

        await self._finish_typed_input(query, user_to_state, confirmation)

    ############
    # TRAINERS #
    ############

    async def _show_trainers_menu(self, query):
        team = self.team_service.current_team()
        names = dict(self._roster_members())

        def render(trainer_ids: list[int]) -> str:
            if not trainer_ids:
                return Format.italic(t('group chat (no trainers set)'))
            return Format.escape(', '.join(names.get(chat_id, str(chat_id)) for chat_id in trainer_ids))

        message = t('<b>Trainers</b>\n'
                    'Attendance summaries and warnings go to the trainers of each event group; '
                    'a group without trainers uses the team group chat instead.\n\n'
                    '{games_label}: {games}\n'
                    '{training_label}: {training}',
                    games_label=t(AdminMenu.TRAINER_GROUP_LABELS[Event.GAME]),
                    games=render(team.trainers_games),
                    training_label=t(AdminMenu.TRAINER_GROUP_LABELS[Event.TRAINING]),
                    training=render(team.trainers_training))
        await self._edit(query, message, AdminMenu.build_trainers_menu_markup())

    async def _show_trainer_list(self, query, event_type: Event):
        trainer_ids = self.team_service.current_team().trainers_for(event_type)
        entries = self._trainer_candidates(trainer_ids)
        message = t('{group_label} - tap a person to add or remove them '
                    'as trainer. Changes apply immediately.',
                    group_label=t(AdminMenu.TRAINER_GROUP_LABELS[event_type]))
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
        await self.add_event_node.update_inline_message(temp_data, t('Adding new'), can_save=False)
        await self.add_event_node.replace_prompt(update, temp_data, EventField.DATETIME)
        self.event_service.save_draft(temp_data)

    async def _handle_wizard_action(self, update: Update, query, action: str):
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        try:
            temp_data = self.event_service.get_draft(user_to_state.user_id)
        except NoTempDataFoundException:
            # Stale button: the draft was already saved or discarded.
            await self._edit(query, t('This draft is no longer active - start again via the admin menu.'))
            return

        match action:
            case AdminMenu.WIZARD_CANCEL:
                await self.add_event_node.abort_draft(user_to_state)
                self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
                await self._edit(query, t('Cancelled - the event was not saved.'))
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
