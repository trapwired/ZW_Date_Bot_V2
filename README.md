# ZW_Date_Bot_V2

A Telegram bot (built on [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot))
that manages a sports team's schedule — games, trainings and timekeeping events — and
tracks each player's attendance.

## Architecture

Interactive diagram:
**[Architecture Overview (Excalidraw)](https://app.excalidraw.com/s/3a3Hj2SHqi7/eD5BdVpW7v)**
— the request pipeline, feature slices, and background jobs at a glance.

The codebase is organized as **vertical slices** on a shared spine:

```
src/
  framework/   feature-agnostic runtime: NodeHandler, Node/CallbackNode, Transitions,
               TelegramService, UserStateService, SchedulingService, ...
  features/    one folder per capability, each owning its Node(s) + Service:
               eventmgmt · attendance · stats · roles · website · onboarding · menu
  domain/      entities + business rules (policies, parsing) — no Telegram, no SQL
  data/        DataAccess + PostgresRepository (the storage boundary)
  Enums/  Utils/   shared cross-cutting code
```

**Request path.** A Telegram update reaches `NodeHandler`, which routes by the user's
`UserState`: plain text goes to a feature **Node**, an inline-button tap goes to a
**CallbackNode**. The node parses the input, calls its slice **Service** for
orchestration, which reads/writes through **`domain`** models and the **`data`** layer
to **Postgres**; the reply is sent back out via `TelegramService`.

**Background jobs.** `SchedulingService` runs on APScheduler to send attendance
reminders and trainer summaries, reading events via `data` and sending via
`TelegramService`.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full description, with key
decisions in [`docs/adr/`](docs/adr).

## Setup

Two things are required to run the bot: a Telegram bot token and a Postgres to
connect to. Put the api-token and the `[Database]` dsn in `secrets/api_config.ini`
— an example `api-config.ini` is included in that folder; just replace the values.
For a full local stack (bot + Postgres in docker) see
[`docs/local-dev.md`](docs/local-dev.md).

## Reference

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Telegram Bot API](https://core.telegram.org/bots/api)
