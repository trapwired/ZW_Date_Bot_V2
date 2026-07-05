# ADR 0004: Per-user language (i18n)

## Status
Accepted (2026-07-05)

## Context
All bot copy was hardcoded English. Users are Swiss handball players; the bot
should speak each user's language. Five languages: English (`en`), Hochdeutsch
(`de`), Züridütsch (`gsw`), French (`fr`), Italian (`it`).

Telegram offers no per-user message translation. What it does offer:
- `update.effective_user.language_code` — the client's UI language, on every
  update (optional field; `gsw` is never reported, Swiss clients say `de`).
- Localized command menus / bot descriptions via
  `set_my_commands(language_code=...)` (two-letter codes only, so no `gsw`).

## Decision

**Catalog: English string = key.** Flat JSON per language under
`src/localization/locales/<lang>.json`; `en` needs no file (the key is the
text). Dynamic parts are named `{placeholders}` filled by `t(text, **params)`;
params arrive pre-escaped, catalog values may contain our own HTML markup.
Chosen over stable message-ids for greppability: the English text in the code
IS what the user sees.

**Ambient language, resolved once per unit of work.** Mirror of the tenant
context (ADR 0001): a contextvar in `localization/LanguageContext.py`, set by
`NodeHandler` per update — saved choice (`UsersToState.language`) → client
`language_code` → `en`. Fan-out sends (reminders, announce) set it per
recipient; group-chat / trainer sends use `Team.language` (admin ⚙️ Setup;
default `en` so existing groups don't switch silently). Unlike the tenant
context this fails OPEN: wrong language beats no message.

**Unset preference is computed, not migrated.** `language=None` means "follow
the client"; nothing is written until the user picks in `/language`. No
backfill migration, self-healing.

**Reply-keyboard labels decoupled from routing.** Keyboard button text doubles
as command routing (Telegram echoes the label). `CommandLabels` maps canonical
command → localized label at render, and folds incoming text from ANY
supported language back to the canonical command — so a keyboard rendered
before a language switch keeps working. Canonical English is always accepted;
slash commands are never localized.

**Drift guards over discipline.** `localization/KeyExtraction.py` collects all
`t()` keys statically (AST); tests fail on: a key missing from any catalog, an
orphaned catalog entry, placeholder mismatch between key and translation, or a
`t()` call whose key can't be resolved statically.

## Consequences
- Editing an English string is a catalog-key change: all four translations
  must move with it (the parity test enforces this).
- `t()` wraps at composition/send sites only — never module constants at
  import time (would freeze one language at startup).
- Maintainer/diagnostic messages stay English by design.
- `gsw` users get a default-language Telegram command menu (API limitation);
  everything in-chat is fully localized.
