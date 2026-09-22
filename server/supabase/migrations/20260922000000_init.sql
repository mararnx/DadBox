-- DadBox schema. docs/SERVER-CONCEPT.md, PROTOCOL.md v0.3, ADR 0010/0017/0018.
--
-- Two rules shape everything here:
--   * The server cannot read a message. Audio is ciphertext in a private bucket;
--     there is no key column anywhere, and there never will be.
--   * Nothing is reachable except through the Edge Function. RLS is enabled on
--     every table with NO policies, so the auto-generated REST API answers
--     anon/authenticated with nothing. Only service_role (the function) works.

create extension if not exists pg_cron;
create extension if not exists pg_net;

-- --- Identities ---------------------------------------------------------------
-- Three, hardcoded (ADR 0008). Tokens are 256 random bits; only the SHA-256 is
-- stored. token_hash is null until tools/mint_token.py sets it.

create table identities (
  id          text primary key check (id in ('box', 'parent-a', 'parent-b')),
  token_hash  text unique check (token_hash ~ '^[0-9a-f]{64}$'),
  rotated_at  timestamptz
);
insert into identities (id) values ('box'), ('parent-a'), ('parent-b');

create table push_devices (
  identity     text not null references identities,
  apns_token   text not null check (apns_token ~ '^[0-9a-fA-F]{32,200}$'),
  environment  text not null check (environment in ('production', 'sandbox')),
  updated_at   timestamptz not null default now(),
  primary key (identity, apns_token)
);

-- --- Messages -----------------------------------------------------------------
-- `id` is a ULID minted at the recording end — the idempotency key. The server
-- never mints ids. `seq`, not created_at, is the sender's ordering key.
-- Rows are never deleted (ADR 0018).

create table messages (
  id            text primary key check (id ~ '^[0-9A-HJKMNP-TV-Z]{26}$'),
  seq           bigint not null check (seq >= 0),
  sender        text not null references identities,
  recipient     text not null references identities,
  created_at    timestamptz not null,
  time_ok       boolean not null,
  duration_ms   integer not null check (duration_ms between 1 and 300000),
  codec         smallint not null check (codec in (2, 3)),
  key_id        smallint not null check (key_id between 1 and 255),
  bytes         integer not null check (bytes > 0),
  chunk_total   integer check (chunk_total > 0),
  crc32         bigint,
  state         text not null default 'uploading'
                check (state in ('uploading', 'uploaded', 'delivered', 'played')),
  blob_key      text,
  uploaded_at   timestamptz,
  delivered_at  timestamptz,
  played_at     timestamptz,
  updated_at    timestamptz not null default now(),
  unique (sender, seq),
  check (sender <> recipient),
  check (state = 'uploading' or (blob_key is not null and uploaded_at is not null))
);
create index messages_changed on messages (updated_at, id);
create index messages_inbox on messages (recipient, state);

create function touch_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at := clock_timestamp();
  return new;
end $$;
create trigger messages_touch before update on messages
  for each row execute function touch_updated_at();

-- Chunks wait here until `complete`. The primary key IS the idempotency rule:
-- a repeated chunk is an upsert, upload-state is one select.
create table message_chunks (
  message_id  text not null references messages on delete cascade,
  seq         integer not null check (seq >= 0),
  data        bytea not null check (octet_length(data) between 1 and 32768),
  primary key (message_id, seq)
);

-- --- The box ------------------------------------------------------------------

create table box_status (
  id               boolean primary key default true check (id),
  telemetry        jsonb not null,
  last_checkin_at  timestamptz not null,
  next_due_at      timestamptz not null        -- late after this: 2 × next_checkin_s
);

create table checkins (
  at         timestamptz not null default now(),
  telemetry  jsonb not null
);
create index checkins_at on checkins (at);

create table settings (
  id     boolean primary key default true check (id),
  value  jsonb not null,
  meta   jsonb not null default '{}'          -- path → { by, at }: who muted, when
);
insert into settings (value) values ('{
  "poll": { "active_minutes": 1, "active_window_minutes": 90, "idle_minutes": 30 },
  "mute": { "a": false, "b": false },
  "quiet_hours": { "start": "20:00", "end": "07:00", "tz": "Europe/Zurich" },
  "led_brightness": 40,
  "volume": 70
}');

-- One open alert per (kind, ref): a late box pushes once, not every minute.
create table alerts (
  id          bigint generated always as identity primary key,
  kind        text not null check (kind in ('box_late', 'fault', 'battery_low', 'unplayed_48h')),
  ref         text not null default '',        -- message id for unplayed_48h, fault name for fault
  raised_at   timestamptz not null default now(),
  cleared_at  timestamptz
);
create unique index alerts_open on alerts (kind, ref) where cleared_at is null;

create table audit_log (
  id          bigint generated always as identity primary key,
  at          timestamptz not null default now(),
  identity    text not null,
  action      text not null,
  message_id  text,
  detail      jsonb
);

-- --- Functions the Edge Function calls ------------------------------------------

-- true when this call opened the alert — i.e. push now; false when already open.
create function raise_alert(p_kind text, p_ref text default '') returns boolean
language plpgsql as $$
begin
  insert into alerts (kind, ref) values (p_kind, p_ref);
  return true;
exception when unique_violation then
  return false;
end $$;

create function clear_alert(p_kind text, p_ref text default null) returns void
language sql as $$
  update alerts set cleared_at = now()
  where kind = p_kind and cleared_at is null and (p_ref is null or ref = p_ref);
$$;

-- POST /device/checkin in one round trip: it runs every minute on mains.
create function checkin(p_telemetry jsonb) returns jsonb
language plpgsql as $$
declare
  next_s integer := least(greatest(coalesce((p_telemetry ->> 'next_checkin_s')::integer, 1800), 30), 86400);
begin
  insert into checkins (telemetry) values (p_telemetry);
  insert into box_status (id, telemetry, last_checkin_at, next_due_at)
    values (true, p_telemetry, now(), now() + make_interval(secs => 2 * next_s))
    on conflict (id) do update set
      telemetry = excluded.telemetry,
      last_checkin_at = excluded.last_checkin_at,
      next_due_at = excluded.next_due_at;
  perform clear_alert('box_late');
  return jsonb_build_object(
    'settings', (select value from settings),
    'inbox', coalesce((select jsonb_agg(id order by uploaded_at, id) from messages
                       where recipient = 'box' and state in ('uploaded', 'delivered')), '[]'::jsonb));
end $$;

-- The last step of `complete`. Called only after the blob is durably in Storage
-- and its crc verified; the 2xx the box waits for follows this commit (ADR 0010).
create function mark_uploaded(p_id text, p_blob_key text, p_crc32 bigint) returns setof messages
language sql as $$
  update messages set state = 'uploaded', uploaded_at = now(), blob_key = p_blob_key, crc32 = p_crc32
    where id = p_id and state = 'uploading'
  returning *;
$$;

-- --- The clock ------------------------------------------------------------------
-- pg_cron → pg_net → POST {api}/tick every minute. URL and shared secret live in
-- Vault, set once by hand (server/README.md); until then the job does nothing.

create function tick_call() returns void language plpgsql security definer
set search_path = public, vault, net as $$
declare
  v_url    text := (select decrypted_secret from vault.decrypted_secrets where name = 'dadbox_tick_url');
  v_secret text := (select decrypted_secret from vault.decrypted_secrets where name = 'dadbox_tick_secret');
begin
  if v_url is null or v_secret is null then return; end if;
  perform net.http_post(
    url := v_url,
    headers := jsonb_build_object('content-type', 'application/json', 'x-tick-secret', v_secret),
    body := '{}'::jsonb,
    timeout_milliseconds := 10000);
end $$;

-- Housekeeping never touches audio and never reaps an incomplete upload: only
-- chunks of messages that are already safely assembled, and old telemetry.
create function prune() returns void language sql as $$
  delete from message_chunks c using messages m
    where c.message_id = m.id and m.state <> 'uploading';
  delete from checkins where at < now() - interval '30 days';
$$;

select cron.schedule('dadbox-tick', '* * * * *', 'select public.tick_call()');
select cron.schedule('dadbox-prune', '17 * * * *', 'select public.prune()');

-- --- Lock everything -------------------------------------------------------------

alter table identities     enable row level security;
alter table push_devices   enable row level security;
alter table messages       enable row level security;
alter table message_chunks enable row level security;
alter table box_status     enable row level security;
alter table checkins       enable row level security;
alter table settings       enable row level security;
alter table alerts         enable row level security;
alter table audit_log      enable row level security;

revoke all on all tables    in schema public from anon, authenticated;
revoke all on all functions in schema public from anon, authenticated, public;
grant execute on all functions in schema public to service_role;
alter default privileges in schema public revoke all on tables    from anon, authenticated;
alter default privileges in schema public revoke all on functions from anon, authenticated, public;

-- The archive. Private; no policies on storage.objects for it, so only
-- service_role can read or write. Objects are never deleted (ADR 0018).
insert into storage.buckets (id, name, public) values ('audio', 'audio', false)
  on conflict (id) do nothing;
