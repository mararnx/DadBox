-- The lock screen's "message waiting" (ADR 0027). Each device may hand over its
-- ActivityKit push-to-start token; the server starts one Live Activity per
-- waiting message with it and never updates or ends it, so nothing else is kept.
alter table push_devices
  add column live_activity_token text check (live_activity_token ~ '^[0-9a-f]{32,400}$');
