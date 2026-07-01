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