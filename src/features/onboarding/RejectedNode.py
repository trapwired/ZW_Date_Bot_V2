from telegram import Update

from Enums.MessageType import MessageType
from Enums.Role import Role
from Enums.UserState import UserState

from framework.Nodes.Node import Node

from domain.entities.UsersToState import UsersToState


class RejectedNode(Node):

    def __init__(self, state, telegram_service, user_state_service, data_access, team_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.team_service = team_service
        # Free text on the REJECTED screen is a spectator-password attempt.
        self.fallback_action = self.handle_password_attempt

    async def handle_password_attempt(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # The password identifies the team (unique across teams); matching is exact and
        # case-sensitive on the raw text.
        team = self.team_service.find_team_by_spectator_password(update.message.text.strip())
        if team is None:
            await self.handle_help(update, user_to_state, new_state)
            return
        self.user_state_service.join_team(user_to_state, team.doc_id, Role.SPECTATOR)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, UserState.DEFAULT),
            message_type=MessageType.WELCOME,
            message_extra_text=team.name)

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.REJECTED)
