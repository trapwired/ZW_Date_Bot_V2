# Onboarding guide

The bot sends this guide automatically right after the welcome message — role-aware,
from `features/onboarding/WelcomeGuide.py` (players/admins via `/start`, spectators
after entering the spectator password).

This file is the copy-paste version for posting manually in a team's group chat:
existing members joined before the guide existed and won't `/start` again. Replace
`<team>` with the team name. Keep the two in sync when the flows change.

## Players (and admins)

> Here is how you get around the `<team>` manager 🧭
>
> 📅 **Events** — tap `events` in the keyboard below to see upcoming games, trainings
> and timekeeping duties. Open one and answer with Yes / No / Unsure — keeping that
> answer current is all the bot ever asks of you.
>
> 🔔 **Reminders** — no answer yet for an upcoming event? The bot sends you a private
> reminder ahead of time. Answer once and it stays quiet.
>
> 📆 **Calendar** — every event card has a calendar button that sends the event as a
> file for your phone's calendar app.
>
> 🌐 **Website** — tap `website` for the team's page.
>
> ❓ /help shows everything you can do; /privacy explains what data the bot keeps.

Admins additionally get:

> 🛠 **Admin** — tap `admin` for the admin panel: add events, statistics, roles,
> trainers, the website link and the spectator password.

## Spectators

> Here is how you follow `<team>` 🧭
>
> 📅 **Events** — tap `events` in the keyboard below to see upcoming games and
> trainings, including who has signed up.
>
> 🌐 **Website** — tap `website` for the team's page.
>
> ❓ /help shows everything you can do; /privacy explains what data the bot keeps.

## New team admins (setup guide)

Sent automatically as a private message to the group admin who adds the bot to a
group chat (the add itself registers the team, named after the group title). If the
bot cannot message them first, it posts a t.me link in the group instead.

> 🎉 **`<team>`** is registered, and you are its first admin!
>
> Your setup steps — everything lives behind the admin menu (tap `admin` in the
> keyboard below):
>
> 1️⃣ **Spectator password** (🔑) — fans and supporters enter it to follow the team;
> until it is set, nobody can join as spectator.
> 2️⃣ **First event** (➕) — add a game or training so there is something to answer to.
> 3️⃣ **Invite the team** — tell everyone in the group chat to open a private chat
> with me and press Start; group members join as players automatically.
> 4️⃣ Optional: **trainers** (🧑‍🏫) for summaries and warnings, the **website** (🌐)
> link, and a different **team name** (✏️) — I took it from your group title.
>
> Changed your mind? Just remove me from the group chat and everything is rolled back.
