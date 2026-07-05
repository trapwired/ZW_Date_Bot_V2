from framework.Nodes.TypedInputNode import TypedInputNode

from features.adminpanel import AdminMenu

from localization.Translator import t

from Utils import Format


class UpdateWebsiteNode(TypedInputNode):
    """Captures the new website URL an admin types after pressing 'Set website' in the
    admin menu; nothing is persisted until Save (handled by AdminMenuCallbackNode)."""

    cancelled_text = 'Cancelled - the website link was not changed.'

    def confirm_text(self, value: str) -> str:
        return t('Set the website link to:\n{value}\n\nSave it?', value=Format.escape(value))

    def confirm_markup(self):
        return AdminMenu.build_website_confirm_markup()
