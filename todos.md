# ToDos
- [] make bot respond to more than one team
  - add admins on start
  - edit admins
  - set name and everything necessary
- [] broadcast "what's new" to admins (announce feature)
  - reuse the existing fan-out pattern (AddEventFieldsNode.notify_all_players /
    TelegramService); a NotificationService.broadcast(role_set, message) shared
    with the scheduling loops
  - shape as its own vertical slice: prefer an admin `/announce` command over a
    hardcoded deploy-time changelog script
  - do after the Phase 3/4 refactor, not folded into it
- [ ] per-user language switch (i18n)
  - a `language` field on the user (UsersToState/TelegramUser); resolve once per
    update like the tenant context, don't thread it through every call
  - the message/label strings live in Format / PrintUtils / CommandDescriptions —
    that layer becomes the single translation seam (keys -> localized text)
  - decide the string catalog format + fallback language; MessageType is the
    natural key set
- [ ] redesign the menu / submenu experience for accessibility
  - the reply-keyboard layout is built in TelegramService (fixed per-screen
    layouts) + the state -> commands rendering; rework as part of Phase 4 once
    nodes live in feature slices
  - goals: fewer/clearer levels, consistent back/overview, discoverable actions
- [ ] make `/help` always list AND explain every currently-available option
  - `do_checks.check_all_commands_have_description` already fails the suite if a
    described command lacks a description; extend the guarantee so help renders
    every active transition for the user's state+role with its explanation
  - single source of truth: CommandDescriptions; help should derive from the same
    transitions the keyboard does (get_commands_for_help), so they can't drift