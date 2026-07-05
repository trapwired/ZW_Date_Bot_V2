from framework.Nodes.TypedInputNode import TypedInputNode

from features.adminpanel import AdminMenu

from Utils import Format


class UpdateWebsiteNode(TypedInputNode):
    """Captures the new website URL an admin types after pressing 'Set website' in the
    admin menu; nothing is persisted until Save (handled by AdminMenuCallbackNode)."""

    cancelled_text = 'Cancelled - the website link was not changed.'

    def confirm_text(self, value: str) -> str:
        return f'Set the website link to:\n{Format.escape(value)}\n\nSave it?'

    def confirm_markup(self):
        return AdminMenu.build_website_confirm_markup()
