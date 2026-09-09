-- ZW Date Bot relational schema (Stage B of the VPS migration, ADR decisions
-- 2026-07-21): one attendance table with an event_type discriminator, Firestore
-- doc-ids preserved as text PKs (new rows mint uuids), team subcollections
-- become a team_id column. Idempotent: applied at every repository start.

CREATE TABLE IF NOT EXISTS users (
    id          text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    telegram_id bigint NOT NULL,
    firstname   text,
    lastname    text
);
CREATE INDEX IF NOT EXISTS users_telegram_id ON users (telegram_id);

CREATE TABLE IF NOT EXISTS users_to_state (
    id              text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id         text NOT NULL,
    state           integer NOT NULL,
    additional_info text NOT NULL DEFAULT '',
    role            integer NOT NULL,
    is_admin        boolean NOT NULL DEFAULT false,
    team_id         text,
    language        text
);
CREATE INDEX IF NOT EXISTS users_to_state_user_id ON users_to_state (user_id);
CREATE INDEX IF NOT EXISTS users_to_state_team_role ON users_to_state (team_id, role);

CREATE TABLE IF NOT EXISTS teams (
    id                 text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name               text,
    group_chat_id      bigint,
    spectator_password text,
    trainers_games     bigint[] NOT NULL DEFAULT '{}',
    trainers_training  bigint[] NOT NULL DEFAULT '{}',
    invite_tokens      text[]   NOT NULL DEFAULT '{}',
    language           text     NOT NULL DEFAULT 'en'
);

CREATE TABLE IF NOT EXISTS games (
    id          text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    team_id     text NOT NULL,
    timestamp   timestamptz,
    location    text,
    opponent    text,
    -- SHV matchcenter objectId for API-synced games; NULL for manually added ones.
    shv_game_id bigint
);
CREATE INDEX IF NOT EXISTS games_team_ts ON games (team_id, timestamp);
ALTER TABLE games ADD COLUMN IF NOT EXISTS shv_game_id bigint;

CREATE TABLE IF NOT EXISTS trainings (
    id        text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    team_id   text NOT NULL,
    timestamp timestamptz,
    location  text
);
CREATE INDEX IF NOT EXISTS trainings_team_ts ON trainings (team_id, timestamp);

CREATE TABLE IF NOT EXISTS timekeepings (
    id              text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    team_id         text NOT NULL,
    timestamp       timestamptz,
    location        text,
    people_required integer
);
CREATE INDEX IF NOT EXISTS timekeepings_team_ts ON timekeepings (team_id, timestamp);

-- ONE table for all three Firestore attendance collections; event_type holds
-- the Enums.Event int and stands in for "which collection".
CREATE TABLE IF NOT EXISTS attendance (
    id         text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    team_id    text NOT NULL,
    event_type integer NOT NULL,
    user_id    text NOT NULL,
    event_id   text NOT NULL,
    state      integer NOT NULL
);
CREATE INDEX IF NOT EXISTS attendance_event ON attendance (team_id, event_type, event_id);
CREATE INDEX IF NOT EXISTS attendance_user ON attendance (team_id, event_type, user_id);

CREATE TABLE IF NOT EXISTS player_metric (
    id                          text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    team_id                     text NOT NULL,
    user_id                     text NOT NULL,
    game_reminders_sent         integer NOT NULL DEFAULT 0,
    training_reminders_sent     integer NOT NULL DEFAULT 0,
    timekeeping_reminders_sent  integer NOT NULL DEFAULT 0,
    insert_timestamp            timestamptz
);
CREATE INDEX IF NOT EXISTS player_metric_user ON player_metric (team_id, user_id, insert_timestamp);

CREATE TABLE IF NOT EXISTS temp_data (
    id                text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    team_id           text NOT NULL,
    user_doc_id       text NOT NULL,
    timestamp         timestamptz,
    location          text,
    opponent          text,
    chat_id           bigint,
    query_id          text,
    step              integer,
    event_type        integer,
    prompt_message_id bigint
);
CREATE INDEX IF NOT EXISTS temp_data_user ON temp_data (team_id, user_doc_id);

-- Open and answered questions of the SHV schedule sync (create/adopt/delete
-- prompts to the admins). token = the short id carried in the inline buttons
-- (uuids would blow Telegram's 64-byte callback_data budget).
CREATE TABLE IF NOT EXISTS shv_sync_decisions (
    id          text PRIMARY KEY DEFAULT gen_random_uuid()::text,
    team_id     text NOT NULL,
    token       text NOT NULL,
    kind        integer NOT NULL,
    status      integer NOT NULL,
    shv_game_id bigint,
    game_doc_id text,
    reason      text,
    asked_at    timestamptz
);
CREATE INDEX IF NOT EXISTS shv_sync_decisions_team ON shv_sync_decisions (team_id);

-- Firestore held one settings doc per team under the fixed id 'config'; the id
-- column keeps that shape so get/set semantics carry over unchanged.
CREATE TABLE IF NOT EXISTS settings (
    id                text NOT NULL,
    team_id           text NOT NULL,
    website           text,
    -- Maintainer switch: the SHV schedule sync derives its team id from the website
    -- and runs unless this is set (for teams whose portal the sync cannot read).
    shv_sync_disabled boolean NOT NULL DEFAULT false,
    PRIMARY KEY (team_id, id)
);
ALTER TABLE settings ADD COLUMN IF NOT EXISTS shv_sync_disabled boolean NOT NULL DEFAULT false;
