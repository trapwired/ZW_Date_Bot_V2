# VPS handoff: ZW Date Bot calendar feed (`zwbot.fluffyoctopus.ch`)

**For:** the DomiCloud chat (🖥️ = it runs it as `ubuntu`) and Domi (👤 = registrar, secrets, recreating prod containers). **From:** the ZW bot chat, no server access; **nothing below has been executed.** The feed is a Python aiohttp server inside the bot container on `:8080`, dormant until `[Calendar] public_origin` is set (spec: `docs/CALENDAR_FEED_PLAN.md` §4, §8, §11). Read first: `VPS_HANDOVER.md` and the `CLAUDE.md` traps 2, 14, 15, 17b. Start every 🖥️ step with `git fetch` and a hash/mtime check of the target file (trap 15).

## 1. DNS (👤, registrar of fluffyoctopus.ch)
`A zwbot.fluffyoctopus.ch → 179.237.110.135`. 🖥️ confirms it on the authoritative NS (`dig +short @<ns> zwbot.fluffyoctopus.ch`) **before step 4** (trap 2: a Caddy block that outlives its DNS sits in ACME backoff, `docker restart caddy` clears it).

## 2. Server `compose.yml` (🖥️), `/srv/apps/zwdatebot/compose.yml`
Mirror `deploy/compose.yml` (the repo copy is the reference; diff the two). Only delta to today's server file: the bot service joins `web`, no `ports:`.
```yaml
    networks:        # on the zwdatebot service
      - default
      - db
      - web
networks:            # top level, next to db
  web:
    external: true
```
Backup `compose.yml.bak-<date>-web`, exact-string edit, `docker compose config -q`. The container is recreated once for this (by step 3's deploy, or by hand: `docker compose up -d --no-deps zwdatebot`, 👤 since the agent boundary refuses prod recreates). Never a bare `compose pull` here: it would also pull `postgres:16` and recreate the database (the deployer pins the service).

## 3. Server `api_config.ini` (👤 or 🖥️ append-only; never print the file, it holds the token and dsn)
`/srv/apps/zwdatebot/secrets/api_config.ini`. Append one section (no `[Tables]` key needed: the Postgres backend hardcodes its table names):
```ini
[Calendar]
public_origin = https://zwbot.fluffyoctopus.ch
http_port = 8080
```
Safe to do before the code is deployed (the old image ignores it). No DB step: the bot creates `calendar_tokens` at startup. The new image must be live first for anything to listen: after the feed PR is merged, the signed-webhook deploy recreates the container and picks up steps 2 and 3 in one go.

## 4. Caddy site block (🖥️, after DNS resolves), `/srv/apps/caddy/Caddyfile`
```
zwbot.fluffyoctopus.ch {
    import sec_headers
    import accesslog
    reverse_proxy zwdatebot:8080
}
```
House procedure: candidate validated in a throwaway `caddy:2`, append with `cat >>` (keeps the inode, trap 17b), reload. The token sits in the URL path, so it lands in `access.log`: accepted (same as JugiBot); drop `import accesslog` for this host if you would rather not.

## 5. Switch-on checks (🖥️, then 👤 on real devices)
1. `docker network inspect web` lists `zwdatebot`; `docker logs --since 5m zwdatebot` has no traceback; the healthchecks.io ping stays green.
2. `docker exec zwdatebot python -c "import urllib.request as u; print(u.urlopen('http://127.0.0.1:8080/healthz').status)"` → `200`.
3. `curl -i https://zwbot.fluffyoctopus.ch/cal/x.ics` → `404`, `text/plain`, `Cache-Control: no-store`, a body starting «Dieser Kalender-Link gilt nicht mehr.», each `sec_headers` header exactly once (trap 14).
4. 👤 In the real bot: events menu → «📆 Kalender abonnieren», subscribe on iPhone and Google, then plan §10 «Real devices».

Rollback: remove the Caddy block and reload (feed dark), or empty `public_origin` and recreate (bot polls as before). The `web` network on the bot stays harmless.
