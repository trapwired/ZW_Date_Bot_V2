from framework.Nodes.TypedInputNode import TypedInputNode

from features.adminpanel import AdminMenu

from localization.Translator import t

from Utils import Format


class UpdateTeamNameNode(TypedInputNode):
    """Captures the new team name an admin types after pressing 'Team name' in the
    admin menu; nothing is persisted until Save (handled by AdminMenuCallbackNode)."""

    cancelled_text = 'Cancelled - the team name was not changed.'

    def confirm_text(self, value: str) -> str:
        return t('Rename the team to:\n{value}\n\nSave it?', value=Format.escape(value))

    def confirm_markup(self):
        return AdminMenu.build_team_name_confirm_markup()
