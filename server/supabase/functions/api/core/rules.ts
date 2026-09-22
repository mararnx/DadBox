// The protocol's rules, with no I/O: who may do what, what a valid message
// looks like, how settings may change. PROTOCOL.md is the contract; change it
// there first. Framework-free so the tests run on the Mac in milliseconds.

import { FLAG_ENCRYPTED, type Header } from './container.ts'

export type Identity = 'box' | 'parent-a' | 'parent-b'
export const PARENTS: Identity[] = ['parent-a', 'parent-b']
export const isParent = (who: Identity) => who !== 'box'

export const CHUNK_BYTES = 32 * 1024
export const MAX_DURATION_MS = 5 * 60 * 1000
// 5 min of AAC at a generous bitrate, plus envelope. A ceiling, not a target.
export const MAX_MESSAGE_BYTES = 4 * 1024 * 1024

const ULID = /^[0-9A-HJKMNP-TV-Z]{26}$/
export const isUlid = (s: string) => ULID.test(s)

// What the client sends on PUT /messages/{id}.
export type Metadata = {
  seq: number
  to: Identity
  created_at: string
  time_ok: boolean
  duration_ms: number
  codec: number
  key_id: number
  bytes: number
}

// A row of `messages`. `sender`/`recipient` because from/to are SQL keywords.
export type MessageRow = {
  id: string
  seq: number
  sender: Identity
  recipient: Identity
  created_at: string
  time_ok: boolean
  duration_ms: number
  codec: number
  key_id: number
  bytes: number
  chunk_total: number | null
  state: 'uploading' | 'uploaded' | 'delivered' | 'played'
  uploaded_at: string | null
  delivered_at: string | null
  played_at: string | null
  updated_at: string
}

const isInt = (n: unknown, min: number, max: number): n is number =>
  typeof n === 'number' && Number.isInteger(n) && n >= min && n <= max

export function validateMetadata(from: Identity, m: unknown): Metadata | { error: string } {
  if (typeof m !== 'object' || m === null) return { error: 'body must be a JSON object' }
  const b = m as Record<string, unknown>
  if (!isInt(b.seq, 0, Number.MAX_SAFE_INTEGER)) return { error: 'seq' }
  if (b.to !== 'box' && b.to !== 'parent-a' && b.to !== 'parent-b') return { error: 'to' }
  if (typeof b.created_at !== 'string' || Number.isNaN(Date.parse(b.created_at))) return { error: 'created_at' }
  if (typeof b.time_ok !== 'boolean') return { error: 'time_ok' }
  if (!isInt(b.duration_ms, 1, MAX_DURATION_MS)) return { error: 'duration_ms' }
  if (b.codec !== 2 && b.codec !== 3) return { error: 'codec' }
  if (!isInt(b.key_id, 1, 255)) return { error: 'key_id' }
  if (!isInt(b.bytes, 1, MAX_MESSAGE_BYTES)) return { error: 'bytes' }
  const route = routeAllowed(from, b.to)
  if (route !== true) return { error: route }
  return {
    seq: b.seq, to: b.to, created_at: new Date(b.created_at).toISOString(), time_ok: b.time_ok,
    duration_ms: b.duration_ms, codec: b.codec, key_id: b.key_id, bytes: b.bytes,
  }
}

// v1 routing (ADR 0008): the box always sends to parent-a; parents send to the box.
export function routeAllowed(from: Identity, to: Identity): true | string {
  if (from === 'box') return to === 'parent-a' ? true : 'v1: the box sends to parent-a only'
  return to === 'box' ? true : 'parents send to the box only'
}

export function sameMetadata(row: MessageRow, m: Metadata): boolean {
  return row.seq === m.seq && row.recipient === m.to && row.time_ok === m.time_ok &&
    row.duration_ms === m.duration_ms && row.codec === m.codec && row.key_id === m.key_id &&
    row.bytes === m.bytes && Date.parse(row.created_at) === Date.parse(m.created_at)
}

export const chunkTotalFor = (bytes: number) => Math.ceil(bytes / CHUNK_BYTES)

export function missingChunks(received: number[], total: number): number[] {
  const have = new Set(received)
  const missing: number[] = []
  for (let i = 0; i < total; i++) if (!have.has(i)) missing.push(i)
  return missing
}

// What `complete` checks before it may say 2xx (ADR 0010 item 4). The crc is
// checked separately; this is everything the header can contradict.
export function headerMatches(h: Header, row: MessageRow): true | string {
  if (!(h.flags & FLAG_ENCRYPTED)) return 'not encrypted — refused'
  if (h.codec !== row.codec) return 'codec differs from metadata'
  if (h.durationMs !== row.duration_ms) return 'duration_ms differs from metadata'
  if (h.keyId !== row.key_id) return 'key_id differs from metadata'
  if (h.channels !== 1) return 'channels'
  return true
}

// Tokens are scoped (PROTOCOL.md § Identities). The box reaches only its
// current inbox — never history — so a pulled SD card cannot read the archive.
export function canFetchAudio(who: Identity, row: MessageRow): boolean {
  if (row.state === 'uploading') return false
  if (who === 'box') return row.recipient === 'box' && row.state !== 'played'
  return row.sender === who || row.recipient === who
}

export const canSeeMessage = (who: Identity, row: MessageRow) =>
  isParent(who) && (row.sender === who || row.recipient === who)

export const inBoxInbox = (row: MessageRow) =>
  row.recipient === 'box' && (row.state === 'uploaded' || row.state === 'delivered')

export function toWire(row: MessageRow) {
  return {
    id: row.id, seq: row.seq, from: row.sender, to: row.recipient, created_at: row.created_at,
    time_ok: row.time_ok, duration_ms: row.duration_ms, codec: row.codec, key_id: row.key_id,
    bytes: row.bytes, state: row.state, uploaded_at: row.uploaded_at,
    delivered_at: row.delivered_at, played_at: row.played_at,
  }
}

// Range: bytes=a-b | bytes=a- | bytes=-n. One range only; anything else → whole file.
export function parseRange(header: string | null, size: number): { start: number; end: number } | null | 'unsatisfiable' {
  if (!header) return null
  const m = /^bytes=(\d*)-(\d*)$/.exec(header.trim())
  if (!m || (m[1] === '' && m[2] === '')) return null
  let start: number, end: number
  if (m[1] === '') {
    const n = parseInt(m[2], 10)
    if (n === 0) return 'unsatisfiable'
    start = Math.max(0, size - n)
    end = size - 1
  } else {
    start = parseInt(m[1], 10)
    end = m[2] === '' ? size - 1 : Math.min(parseInt(m[2], 10), size - 1)
  }
  if (start >= size || start > end) return 'unsatisfiable'
  return { start, end }
}

// --- Settings ----------------------------------------------------------------

export type Settings = {
  poll: { active_minutes: number; active_window_minutes: number; idle_minutes: number }
  mute: { a: boolean; b: boolean }
  quiet_hours: { start: string; end: string; tz: string }
  led_brightness: number
  volume: number
}

export const DEFAULT_SETTINGS: Settings = {
  poll: { active_minutes: 1, active_window_minutes: 90, idle_minutes: 30 },
  mute: { a: false, b: false },
  quiet_hours: { start: '20:00', end: '07:00', tz: 'Europe/Zurich' },
  led_brightness: 40,
  volume: 70,
}

const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/
const LIMITS: Record<string, (v: unknown) => boolean> = {
  'poll.active_minutes': (v) => isInt(v, 1, 10),
  'poll.active_window_minutes': (v) => isInt(v, 10, 240),
  'poll.idle_minutes': (v) => isInt(v, 5, 60),
  'mute.a': (v) => typeof v === 'boolean',
  'mute.b': (v) => typeof v === 'boolean',
  'quiet_hours.start': (v) => typeof v === 'string' && HHMM.test(v),
  'quiet_hours.end': (v) => typeof v === 'string' && HHMM.test(v),
  'quiet_hours.tz': (v) => typeof v === 'string' && /^[A-Za-z_]+\/[A-Za-z_+\-/]+$/.test(v),
  'led_brightness': (v) => isInt(v, 0, 100),
  'volume': (v) => isInt(v, 0, 100),
}

export type SettingsMeta = Record<string, { by: Identity; at: string }>

// Apply a partial settings object. A parent may set only its own mute; every
// changed field records who and when. Returns the HTTP status to answer with.
export function patchSettings(
  who: Identity, current: Settings, meta: SettingsMeta, patch: unknown, now: string,
): { settings: Settings; meta: SettingsMeta; changed: string[] } | { status: 400 | 403; error: string } {
  if (!isParent(who)) return { status: 403, error: 'parents only' }
  if (typeof patch !== 'object' || patch === null || Array.isArray(patch)) return { status: 400, error: 'body must be a JSON object' }
  const flat: [string, unknown][] = []
  for (const [k, v] of Object.entries(patch as Record<string, unknown>)) {
    if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
      for (const [k2, v2] of Object.entries(v as Record<string, unknown>)) flat.push([`${k}.${k2}`, v2])
    } else flat.push([k, v])
  }
  const next = structuredClone(current) as unknown as Record<string, unknown>
  const nextMeta = { ...meta }
  const changed: string[] = []
  for (const [path, value] of flat) {
    const ok = LIMITS[path]
    if (!ok) return { status: 400, error: `unknown setting ${path}` }
    if (!ok(value)) return { status: 400, error: `invalid value for ${path}` }
    const ownMute = who === 'parent-a' ? 'mute.a' : 'mute.b'
    if (path.startsWith('mute.') && path !== ownMute) return { status: 403, error: `${path} is not yours to set` }
    const [a, b] = path.split('.')
    const before = b ? (next[a] as Record<string, unknown>)[b] : next[a]
    if (before === value) continue
    if (b) (next[a] as Record<string, unknown>)[b] = value
    else next[a] = value
    nextMeta[path] = { by: who, at: now }
    changed.push(path)
  }
  return { settings: next as unknown as Settings, meta: nextMeta, changed }
}

// --- Cursor ------------------------------------------------------------------
// Opaque to clients. Orders by (updated_at, id) so "what is new or changed
// since" is one index scan.

export function encodeCursor(updatedAt: string, id: string): string {
  return btoa(`${updatedAt}|${id}`).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')
}

export function decodeCursor(c: string): { updatedAt: string; id: string } | null {
  try {
    const [updatedAt, id] = atob(c.replaceAll('-', '+').replaceAll('_', '/')).split('|')
    if (!id || Number.isNaN(Date.parse(updatedAt)) || !isUlid(id)) return null
    return { updatedAt, id }
  } catch {
    return null
  }
}
