-- The doorbell (ADR 0021, PROTOCOL.md § Doorbell).
--
-- The database rings, not the Edge Function: a trigger on the two things the
-- box must hear about calls realtime.send() inside the same transaction, and
-- Realtime broadcasts only what has committed. So the bell never rings for a
-- message that is not yet durable, and no code path can forget to ring.
--
-- The ring is empty. It is sent on a public channel whose topic is 128+ random
-- bits, generated here, kept only in Vault and on the box. Anyone who learned
-- it could make the box check in more often — and learn nothing more.

-- --- The topic ---------------------------------------------------------------------
-- Two random UUIDs: 244 random bits, from pg_strong_random. Never in the repo.
select vault.create_secret(
         'doorbell:' || replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', ''),
         'dadbox_doorbell_topic',
         'ADR 0021: the Realtime topic the box joins. Rotate by updating it; the box follows at its next check-in.')
where not exists (select 1 from vault.secrets where name = 'dadbox_doorbell_topic');

create function doorbell_topic() returns text language sql stable security definer
set search_path = public, vault as $$
  select decrypted_secret from vault.decrypted_secrets where name = 'dadbox_doorbell_topic';
$$;

-- --- The ring ----------------------------------------------------------------------
-- A doorbell failure must never fail the write that caused it: `complete`
-- answering 2xx is what lets the box delete its copy (ADR 0010). So the send
-- runs in its own subtransaction and a failure is only a warning — the box
-- still hears about it at its next check-in.
create function ring_doorbell() returns trigger language plpgsql security definer
set search_path = public, realtime as $$
declare
  t text := doorbell_topic();
begin
  if t is not null then
    begin
      perform realtime.send('{}'::jsonb, 'ring', t, false);
    exception when others then
      raise warning 'doorbell: % (the box will hear at its next check-in)', sqlerrm;
    end;
  end if;
  return null;
end $$;

-- The settings grow the backstop before the settings trigger exists, so this
-- update does not ring.
update settings set value = jsonb_set(value, '{poll,backstop_minutes}', '10')
  where value -> 'poll' -> 'backstop_minutes' is null;

create trigger ring_on_message_for_box
  after update of state on messages
  for each row
  when (new.recipient = 'box' and old.state = 'uploading' and new.state = 'uploaded')
  execute function ring_doorbell();

create trigger ring_on_settings
  after update on settings
  for each row
  when (old.value is distinct from new.value)
  execute function ring_doorbell();

-- --- The check-in hands the box its topic ---------------------------------------------
-- The Edge Function wraps it into { url, topic }; the URL is this project's
-- Realtime with the publishable key, which the database does not know.
create or replace function checkin(p_telemetry jsonb) returns jsonb
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
                       where recipient = 'box' and state in ('uploaded', 'delivered')), '[]'::jsonb),
    'doorbell_topic', doorbell_topic());
end $$;

revoke all on function doorbell_topic() from public, anon, authenticated;
revoke all on function ring_doorbell()  from public, anon, authenticated;
grant execute on function doorbell_topic() to service_role;
