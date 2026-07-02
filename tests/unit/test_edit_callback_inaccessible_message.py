"""Unit: edit_callback_message must survive buttons on messages older than 48 hours.

For those, Telegram delivers only an InaccessibleMessage in the callback -
CallbackQuery.edit_message_text raises TypeError, but the message can still be edited
directly via its chat/message ids. Old menu buttons and legacy attendance buttons sit
on exactly such messages, so this path is what keeps them working.
"""
from types import SimpleNamespace

from telegram import Chat, InaccessibleMessage


def _query_with(message):
    async def _fail_edit(*args, **kwargs):
        raise AssertionError("query.edit_message_text must not be used for inaccessible messages")
    return SimpleNamespace(message=message, from_user=SimpleNamespace(id=42), edit_message_text=_fail_edit)


async def test_inaccessible_message_is_edited_via_its_ids(services, bot):
    telegram_service = services["telegram_service"]
    query = _query_with(InaccessibleMessage(chat=Chat(id=7, type="private"), message_id=99))

    await telegram_service.edit_callback_message(query, "new text")

    assert len(bot.edits) == 1
    assert (bot.edits[0].chat_id, bot.edits[0].message_id, bot.edits[0].text) == (7, 99, "new text")


async def test_missing_message_falls_back_to_a_new_message(services, bot):
    telegram_service = services["telegram_service"]
    query = _query_with(None)

    await telegram_service.edit_callback_message(query, "new text")

    assert bot.edits == []
    assert [m.chat_id for m in bot.sent] == [42]
