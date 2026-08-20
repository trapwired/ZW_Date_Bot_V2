from framework.Nodes.TypedInputNode import TypedInputNode

from features.roles import RoleAssignment

from localization.Translator import t

from Utils import Format


class RenamePlayerNode(TypedInputNode):
    """Captures the new name an admin types for a player after pressing 'Change name'
    in the roles menu; nothing is persisted until Save (handled by
    AssignRolesCallbackNode). The staging slot keeps '<target_doc_id>#<typed name>'
    so the Save press knows whom to rename."""

    cancelled_text = 'Cancelled - the name was not changed.'

    def staged_value(self, previous_value: str, typed: str) -> str:
        target_doc_id, _ = RoleAssignment.unpack_rename_value(previous_value)
        return RoleAssignment.pack_rename_value(target_doc_id, typed)

    def confirm_text(self, value: str) -> str:
        return t('Rename this player to:\n{value}\n\nSave it?', value=Format.escape(value))

    def confirm_markup(self):
        return RoleAssignment.build_rename_confirm_markup()
