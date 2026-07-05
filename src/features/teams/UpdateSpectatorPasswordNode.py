from framework.Nodes.TypedInputNode import TypedInputNode

from features.adminpanel import AdminMenu

from localization.Translator import t

from Utils import Format


class UpdateSpectatorPasswordNode(TypedInputNode):
    """Captures the new spectator password an admin types after pressing 'Spectator
    password' in the admin menu; nothing is persisted until Save (handled by
    AdminMenuCallbackNode)."""

    cancelled_text = 'Cancelled - the spectator password was not changed.'

    def confirm_text(self, value: str) -> str:
        return t('Set the spectator password to:\n{value}\n\nSave it?', value=Format.escape(value))

    def confirm_markup(self):
        return AdminMenu.build_spectator_password_confirm_markup()
