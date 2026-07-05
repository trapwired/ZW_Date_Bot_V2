from framework.Nodes.TypedInputNode import TypedInputNode

from features.adminpanel import AdminMenu
from features.announce.AnnounceService import render_announcement, TELEGRAM_MESSAGE_LIMIT

from Utils import Format


class AnnounceNode(TypedInputNode):
    """Captures the announcement text an admin types after pressing 'Announce' in the
    admin menu; nothing is sent until they pick a delivery channel (handled by
    AdminMenuCallbackNode)."""

    cancelled_text = 'Cancelled - nothing was announced.'

    def confirm_text(self, value: str) -> str:
        return f'Send this announcement?\n\n{Format.escape(value)}'

    def confirm_markup(self):
        return AdminMenu.build_announce_confirm_markup()

    def review_value(self, value: str) -> tuple[str, object] | None:
        overlength = len(render_announcement(value)) - TELEGRAM_MESSAGE_LIMIT
        if overlength > 0:
            return (f'⚠️ That announcement is about {overlength} characters too long for one '
                    'Telegram message - please shorten it and send it again.',
                    AdminMenu.build_typed_input_prompt_markup())
        return None
