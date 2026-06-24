import html

# Single source of truth for outbound message formatting. All messages are sent with
# Telegram's HTML parse mode, so the only characters that ever need escaping are & < >.
# Every styling helper escapes its dynamic argument itself, so callers compose safe
# fragments and physically cannot forget to escape user- or DB-supplied content.


def escape(text) -> str:
    return html.escape(str(text), quote=False)


def bold(text) -> str:
    return f'<b>{escape(text)}</b>'


def italic(text) -> str:
    return f'<i>{escape(text)}</i>'


def code(text) -> str:
    return f'<code>{escape(text)}</code>'


def pre(text) -> str:
    # Monospace block - used for diagnostic dumps (tracebacks, raw updates).
    return f'<pre>{escape(text)}</pre>'


def link(text, url: str) -> str:
    return f'<a href="{html.escape(str(url), quote=True)}">{escape(text)}</a>'
