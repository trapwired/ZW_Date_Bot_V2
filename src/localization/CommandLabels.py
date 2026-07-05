"""The bridge between localized button labels and canonical command routing.

Reply-keyboard buttons ARE commands: Telegram echoes the pressed label back as
plain text and Node.handle matches it against Transition.command. Localizing
the display label therefore needs a reverse map - any localized label (from ANY
language, so a keyboard rendered before a language switch keeps working) maps
back to its canonical lowercase command. The canonical English command itself
always stays accepted. Slash commands are never localized.
"""
from localization.Languages import SUPPORTED_LANGUAGES
from localization.Translator import t, translate

# canonical command -> catalog key of its display label.
COMMAND_LABEL_KEYS = {
    'events': 'Events',
    'admin': 'Admin',
    'website': 'Website',
}

# Typed word-commands that are not reply-keyboard buttons but should accept
# their localized forms too: canonical command -> catalog key.
WORD_ALIAS_KEYS = {
    'save': 'SAVE',
    'help': 'help',
}

_reverse_map: dict[str, str] | None = None


def display_label(command: str) -> str:
    """The localized reply-keyboard label for a canonical command; commands
    outside the fixed map keep the previous Title-case behavior, slash commands
    stay verbatim (Telegram matches them literally)."""
    label_key = COMMAND_LABEL_KEYS.get(command)
    if label_key is not None:
        return t(label_key)
    return command if command.startswith('/') else command.title()


def canonical_command(text: str) -> str:
    """Incoming message text resolved to its canonical lowercase command; text
    that matches no localized label passes through lowercased (typed input,
    slash commands, passwords)."""
    lowered = text.lower()
    return _labels_to_commands().get(lowered.strip(), lowered)


def _labels_to_commands() -> dict[str, str]:
    global _reverse_map
    if _reverse_map is None:
        # Built lazily (not at import) so catalogs are complete by first use.
        reverse = {}
        for command, label_key in (COMMAND_LABEL_KEYS | WORD_ALIAS_KEYS).items():
            for language in SUPPORTED_LANGUAGES:
                label = translate(label_key, language).lower().strip()
                collision = reverse.get(label)
                if collision is not None and collision != command:
                    raise ValueError(f'Localized label {label!r} is ambiguous: {collision} vs {command}')
                reverse[label] = command
        _reverse_map = reverse
    return _reverse_map
