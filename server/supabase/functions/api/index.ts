// DadBox API — one Supabase Edge Function speaking docs/PROTOCOL.md v0.3.
// Change the contract there before changing it here.
//
// Hold the audio, wake a phone, know whether the box is alive — without being
// able to listen (ADR 0017) and without ever deleting a message (ADR 0018).
//
// Deployed with verify_jwt = false: Supabase Auth is unused. Every request
// carries one of three bearer tokens, checked below against a SHA-256.
// This file is routes only: parse → core/ → respond. The rules live in core/.

import { type Context, Hono } from 'hono'
import { createClient } from '@supabase/supabase-js'

import { type Device, push, type PushKind } from './apns.ts'
import { concat, crc32, crcOk, fromBytea, parseHeader, toBytea } from './core/container.ts'
import {
  canFetchAudio, canSeeMessage, CHUNK_BYTES, chunkTotalFor, decodeCursor, encodeCursor,
  headerMatches, type Identity, isParent, isUlid, type MessageRow, missingChunks, PARENTS,
  parseRange, patchSettings, sameMetadata, type Settings, type SettingsMeta, toWire,
  validateMetadata,
} from './core/rules.ts'

const db = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, {
  auth: { persistSession: false, autoRefreshToken: false },
})
const BUCKET = 'audio'

type Env = { Variables: { who: Identity } }
const app = new Hono<Env>().basePath('/api')

const fail = (c: Context, status: 400 | 401 | 403 | 404 | 409 | 413 | 416 | 422 | 503, error: string, extra = {}) =>
  c.json({ error, ...extra }, status)

// Work that must not delay the response — pushes, audit rows.
const later = (p: PromiseLike<unknown>) => {
  const guarded = Promise.resolve(p).catch((e) => console.error('background task failed', e))
  // deno-lint-ignore no-explicit-any
  const rt = (globalThis as any).EdgeRuntime
  if (rt?.waitUntil) rt.waitUntil(guarded)
}

const audit = (identity: string, action: string, message_id: string | null = null, detail: unknown = null) =>
  later(db.from('audit_log').insert({ identity, action, message_id, detail }))

async function sha256Hex(s: string): Promise<string> {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

function sameSecret(a: string, b: string): boolean {
  const x = new TextEncoder().encode(a), y = new TextEncoder().encode(b)
  let diff = x.length ^ y.length
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i % Math.max(y.length, 1)]
  return diff === 0
}

async function notify(to: Identity[], kind: PushKind, data: Record<string, unknown> = {}) {
  const { data: devices } = await db.from('push_devices').select('apns_token, environment').in('identity', to)
  const results = await push((devices ?? []) as Device[], kind, data)
  const gone = results.filter((r) => r.gone).map((r) => r.token)
  if (gone.length) await db.from('push_devices').delete().in('apns_token', gone)
}

async function loadMessage(id: string): Promise<MessageRow | null> {
  const { data } = await db.from('messages').select('*').eq('id', id).maybeSingle()
  return data as MessageRow | null
}

// --- The clock (pg_cron → here, every minute) ------------------------------------
// Before the bearer check: it authenticates with its own shared secret.

app.post('/tick', async (c) => {
  const secret = Deno.env.get('TICK_SECRET')
  if (!secret || !sameSecret(c.req.header('x-tick-secret') ?? '', secret)) return fail(c, 401, 'unauthorized')

  // The most important alert in the system: the box has stopped checking in.
  const { data: status } = await db.from('box_status').select('next_due_at, last_checkin_at').maybeSingle()
  if (status && Date.parse(status.next_due_at) < Date.now()) {
    const { data: fresh } = await db.rpc('raise_alert', { p_kind: 'box_late' })
    if (fresh) await notify(PARENTS, 'box_late', { last_checkin_at: status.last_checkin_at })
  }

  // Unplayed messages are surfaced at 48 h — told to their sender, never reaped.
  const cutoff = new Date(Date.now() - 48 * 3600 * 1000).toISOString()
  const { data: waiting } = await db.from('messages').select('id, sender')
    .eq('recipient', 'box').in('state', ['uploaded', 'delivered']).lt('uploaded_at', cutoff)
  for (const m of waiting ?? []) {
    const { data: fresh } = await db.rpc('raise_alert', { p_kind: 'unplayed_48h', p_ref: m.id })
    if (fresh) await notify([m.sender as Identity], 'unplayed_48h', { id: m.id })
  }
  return c.json({ ok: true })
})

// --- Identity on every request -----------------------------------------------------

app.use('*', async (c, next) => {
  const m = /^Bearer\s+(\S+)$/i.exec(c.req.header('authorization') ?? '')
  if (!m) return fail(c, 401, 'unauthorized')
  const { data } = await db.from('identities').select('id').eq('token_hash', await sha256Hex(m[1])).maybeSingle()
  if (!data) return fail(c, 401, 'unauthorized')
  c.set('who', data.id as Identity)
  await next()
})

const parentsOnly = async (c: Context<Env>, next: () => Promise<void>) =>
  isParent(c.get('who')) ? await next() : fail(c, 403, 'parents only')

// --- Messages: upload (either direction) -----------------------------------------------
// `id` is minted by the recording end and is the idempotency key: a retry of
// any of these requests is the same request.

app.put('/messages/:id', async (c) => {
  const who = c.get('who'), id = c.req.param('id')
  if (!isUlid(id)) return fail(c, 400, 'id must be a ULID')
  const meta = validateMetadata(who, await c.req.json().catch(() => null))
  if ('error' in meta) return fail(c, 400, `invalid metadata: ${meta.error}`)

  let row = await loadMessage(id)
  if (!row) {
    const { error } = await db.from('messages').insert({
      id, seq: meta.seq, sender: who, recipient: meta.to, created_at: meta.created_at,
      time_ok: meta.time_ok, duration_ms: meta.duration_ms, codec: meta.codec, key_id: meta.key_id,
      bytes: meta.bytes, chunk_total: chunkTotalFor(meta.bytes),
    })
    if (error && error.code !== '23505') return fail(c, 503, 'could not store metadata')
    row = await loadMessage(id)          // ours, or the one a racing retry just made
    if (!row) return fail(c, 409, 'seq already used by another message')
  }
  if (row.sender !== who || !sameMetadata(row, meta)) return fail(c, 409, 'this id exists with different metadata')
  return c.json(toWire(row))
})

app.put('/messages/:id/chunks/:seq', async (c) => {
  const who = c.get('who'), seq = Number(c.req.param('seq'))
  const row = await loadMessage(c.req.param('id'))
  if (!row || row.sender !== who) return fail(c, 404, 'no such message')
  if (row.state !== 'uploading') return c.json({ ok: true, complete: true })   // a late retry; nothing to do
  const total = Number(c.req.header('x-chunk-total'))
  if (total !== row.chunk_total) return fail(c, 400, `X-Chunk-Total must be ${row.chunk_total}`)
  if (!Number.isInteger(seq) || seq < 0 || seq >= total) return fail(c, 400, 'chunk seq out of range')

  const data = new Uint8Array(await c.req.arrayBuffer())
  const want = seq === total - 1 ? row.bytes - CHUNK_BYTES * (total - 1) : CHUNK_BYTES
  if (data.length > CHUNK_BYTES) return fail(c, 413, 'chunk larger than 32 KB')
  if (data.length !== want) return fail(c, 400, `chunk ${seq} must be ${want} bytes`)

  const { error } = await db.from('message_chunks')
    .upsert({ message_id: row.id, seq, data: toBytea(data) }, { onConflict: 'message_id,seq' })
  if (error) return fail(c, 503, 'could not store chunk')
  return c.json({ ok: true })
})

app.get('/messages/:id/upload-state', async (c) => {
  const row = await loadMessage(c.req.param('id'))
  if (!row || row.sender !== c.get('who')) return fail(c, 404, 'no such message')
  if (row.state !== 'uploading') {
    return c.json({ received: [...Array(row.chunk_total ?? 0).keys()], complete: true })
  }
  const { data, error } = await db.from('message_chunks').select('seq').eq('message_id', row.id).order('seq')
  if (error) return fail(c, 503, 'could not read upload state')
  return c.json({ received: (data ?? []).map((r) => r.seq), complete: false })
})

// 2xx here is the server's promise that the message is safe. The box deletes its
// own copy on it and not before (ADR 0010), so: durable blob first, crc verified,
// row committed — and only then the answer.
app.post('/messages/:id/complete', async (c) => {
  const who = c.get('who')
  const row = await loadMessage(c.req.param('id'))
  if (!row || row.sender !== who) return fail(c, 404, 'no such message')
  if (row.state !== 'uploading') return c.json(toWire(row))                     // idempotent

  const { data: chunks, error } = await db.from('message_chunks').select('seq, data').eq('message_id', row.id).order('seq')
  if (error) return fail(c, 503, 'could not read chunks')
  const missing = missingChunks((chunks ?? []).map((r) => r.seq), row.chunk_total!)
  if (missing.length) return fail(c, 409, 'chunks missing', { missing })

  const container = concat(chunks!.map((r) => fromBytea(r.data as string)))
  if (container.length !== row.bytes) return fail(c, 422, 'assembled size differs from metadata')
  const header = parseHeader(container)
  if ('error' in header) return fail(c, 422, header.error)
  const matches = headerMatches(header, row)
  if (matches !== true) return fail(c, 422, matches)
  if (!crcOk(container)) return fail(c, 422, 'crc mismatch')

  const blobKey = `${row.id}.dbx`
  const stored = await db.storage.from(BUCKET).upload(blobKey, container, {
    contentType: 'application/octet-stream', upsert: true,
  })
  if (stored.error) return fail(c, 503, 'could not store audio')

  const crc = crc32(container.subarray(0, container.length - 4))
  const { data: done, error: markError } = await db.rpc('mark_uploaded', { p_id: row.id, p_blob_key: blobKey, p_crc32: crc })
  if (markError) return fail(c, 503, 'could not commit')
  const final = ((done as MessageRow[] | null)?.[0]) ?? await loadMessage(row.id)  // a racing retry may have won
  if (!final || final.state === 'uploading') return fail(c, 503, 'could not commit')

  if (isParent(final.recipient)) later(notify([final.recipient], 'message', { id: final.id }))
  return c.json(toWire(final))
})

// --- Messages: download ------------------------------------------------------------------

app.get('/messages/:id/audio', async (c) => {
  const who = c.get('who')
  const row = await loadMessage(c.req.param('id'))
  if (!row || !canFetchAudio(who, row)) return fail(c, 404, 'no such message')

  const blob = await db.storage.from(BUCKET).download(`${row.id}.dbx`)
  if (blob.error) return fail(c, 503, 'could not read audio')
  const bytes = new Uint8Array(await blob.data.arrayBuffer())
  const range = parseRange(c.req.header('range') ?? null, bytes.length)
  if (range === 'unsatisfiable') {
    return c.body(null, 416, { 'content-range': `bytes */${bytes.length}` })
  }
  const { start, end } = range ?? { start: 0, end: bytes.length - 1 }

  // Delivered means the recipient has been handed the last byte — not that a
  // download over a dropping link began.
  if (who === row.recipient && row.state === 'uploaded' && end === bytes.length - 1) {
    later(db.from('messages').update({ state: 'delivered', delivered_at: new Date().toISOString() })
      .eq('id', row.id).eq('state', 'uploaded'))
  }
  audit(who, 'audio', row.id, range ? { start, end } : null)
  return c.body(bytes.slice(start, end + 1), range ? 206 : 200, {
    'content-type': 'application/octet-stream',
    'accept-ranges': 'bytes',
    'cache-control': 'no-store',
    ...(range ? { 'content-range': `bytes ${start}-${end}/${bytes.length}` } : {}),
  })
})

// Feedback for the sender. Starts no clock — nothing is ever deleted (ADR 0018).
app.post('/messages/:id/played', async (c) => {
  const who = c.get('who')
  const row = await loadMessage(c.req.param('id'))
  if (!row || row.recipient !== who || row.state === 'uploading') return fail(c, 404, 'no such message')
  if (row.state === 'played') return c.json(toWire(row))
  const now = new Date().toISOString()
  const { data, error } = await db.from('messages')
    .update({ state: 'played', played_at: now, delivered_at: row.delivered_at ?? now })
    .eq('id', row.id).neq('state', 'played').select().maybeSingle()
  if (error) return fail(c, 503, 'could not commit')
  const final = (data as MessageRow | null) ?? (await loadMessage(row.id))!
  audit(who, 'played', row.id)
  later(db.rpc('clear_alert', { p_kind: 'unplayed_48h', p_ref: row.id }).then(() =>
    isParent(final.sender) ? notify([final.sender], 'played', { id: final.id }) : undefined))
  return c.json(toWire(final))
})

// --- Archive and state (parents only) ---------------------------------------------------

app.get('/messages', parentsOnly, async (c) => {
  const who = c.get('who')
  const limit = Math.min(Math.max(Number(c.req.query('limit')) || 100, 1), 500)
  const mine = `sender.eq.${who},recipient.eq.${who}`
  let q = db.from('messages').select('*').neq('state', 'uploading').or(mine)
    .order('updated_at').order('id').limit(limit)
  const raw = c.req.query('cursor')
  if (raw) {
    const cur = decodeCursor(raw)
    if (!cur) return fail(c, 400, 'bad cursor')
    q = q.or(`updated_at.gt."${cur.updatedAt}",and(updated_at.eq."${cur.updatedAt}",id.gt.${cur.id})`)
  }
  const { data, error } = await q
  if (error) return fail(c, 503, 'could not list messages')
  const rows = (data ?? []) as MessageRow[]
  const last = rows[rows.length - 1]
  const { data: top } = await db.from('messages').select('seq').eq('sender', who)
    .order('seq', { ascending: false }).limit(1).maybeSingle()
  return c.json({
    messages: rows.map(toWire),
    cursor: last ? encodeCursor(last.updated_at, last.id) : raw ?? null,
    more: rows.length === limit,
    max_seq: top?.seq ?? null,
  })
})

app.get('/messages/:id', parentsOnly, async (c) => {
  const row = await loadMessage(c.req.param('id') ?? '')
  if (!row || !canSeeMessage(c.get('who'), row)) return fail(c, 404, 'no such message')
  return c.json(toWire(row))
})

async function deviceStatus() {
  const [{ data: status }, { data: settings }] = await Promise.all([
    db.from('box_status').select('*').maybeSingle(),
    db.from('settings').select('value, meta').single(),
  ])
  return {
    telemetry: status?.telemetry ?? null,
    last_checkin_at: status?.last_checkin_at ?? null,
    late: status ? Date.parse(status.next_due_at) < Date.now() : null,   // null: the box has never checked in
    settings: settings!.value as Settings,
    settings_meta: settings!.meta as SettingsMeta,
  }
}

app.get('/device/status', parentsOnly, async (c) => c.json(await deviceStatus()))

app.patch('/settings', parentsOnly, async (c) => {
  const who = c.get('who')
  const { data: cur, error } = await db.from('settings').select('value, meta').single()
  if (error) return fail(c, 503, 'could not read settings')
  const next = patchSettings(who, cur.value as Settings, cur.meta as SettingsMeta,
    await c.req.json().catch(() => null), new Date().toISOString())
  if ('status' in next) return fail(c, next.status, next.error)
  if (next.changed.length) {
    const saved = await db.from('settings').update({ value: next.settings, meta: next.meta }).eq('id', true)
    if (saved.error) return fail(c, 503, 'could not save settings')
    audit(who, 'settings', null, { changed: next.changed })
  }
  return c.json(await deviceStatus())
})

app.put('/push-token', parentsOnly, async (c) => {
  const b = await c.req.json().catch(() => null) as { apns?: unknown; environment?: unknown } | null
  if (typeof b?.apns !== 'string' || !/^[0-9a-fA-F]{32,200}$/.test(b.apns)) return fail(c, 400, 'apns')
  if (b.environment !== 'production' && b.environment !== 'sandbox') return fail(c, 400, 'environment')
  const { error } = await db.from('push_devices').upsert({
    identity: c.get('who'), apns_token: b.apns.toLowerCase(), environment: b.environment,
    updated_at: new Date().toISOString(),
  }, { onConflict: 'identity,apns_token' })
  if (error) return fail(c, 503, 'could not store token')
  return c.json({ ok: true })
})

// --- Device (box only) --------------------------------------------------------------------
// The one request the box makes between events: telemetry in, settings and inbox out.

app.post('/device/checkin', async (c) => {
  if (c.get('who') !== 'box') return fail(c, 403, 'box only')
  const t = await c.req.json().catch(() => null) as Record<string, unknown> | null
  if (typeof t !== 'object' || t === null) return fail(c, 400, 'telemetry must be a JSON object')
  const { data, error } = await db.rpc('checkin', { p_telemetry: t })
  if (error) return fail(c, 503, 'could not check in')

  // Faults and a low battery reach an adult once, not every minute.
  later((async () => {
    if (typeof t.fault === 'string') {
      const { data: fresh } = await db.rpc('raise_alert', { p_kind: 'fault', p_ref: t.fault })
      if (fresh) await notify(PARENTS, 'fault', { fault: t.fault })
    } else await db.rpc('clear_alert', { p_kind: 'fault' })
    const pct = typeof t.battery_pct === 'number' ? t.battery_pct : null
    if (pct !== null && pct < 20 && t.mains === false) {
      const { data: fresh } = await db.rpc('raise_alert', { p_kind: 'battery_low' })
      if (fresh) await notify(PARENTS, 'battery_low', { battery_pct: pct })
    } else if (t.mains === true || (pct !== null && pct >= 30)) {
      await db.rpc('clear_alert', { p_kind: 'battery_low' })     // once per discharge
    }
  })())
  return c.json(data)
})

app.notFound((c) => fail(c, 404, 'not found'))
app.onError((e, c) => {
  console.error(e)
  return fail(c, 503, 'server error')
})

Deno.serve(app.fetch)
