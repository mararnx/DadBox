// node --test   (Node ≥ 23 strips the types; no build step, no dependencies)
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { concat, crc32, crcOk, fromBytea, parseHeader, toBytea } from './container.ts'
import {
  canFetchAudio, chunkTotalFor, decodeCursor, DEFAULT_SETTINGS, doorbellFor, encodeCursor, headerMatches,
  type MessageRow, missingChunks, parseRange, patchSettings, validateMetadata,
} from './rules.ts'

type Vector = { name: string; id: string; codec: number; key_id: number; duration_ms: number; sample_rate: number; container_hex: string }
const VECTORS: Vector[] = JSON.parse(
  readFileSync(new URL('../../../../../docs/testvectors/container-v1.json', import.meta.url), 'utf8'))

const row = (over: Partial<MessageRow> = {}): MessageRow => ({
  id: '01JAYZ3K7QW9E8RVX2M4N6P8TD', seq: 1, sender: 'box', recipient: 'parent-a',
  created_at: '2026-09-20T18:04:11Z', time_ok: true, duration_ms: 14200, codec: 2, key_id: 1,
  bytes: 74, chunk_total: 1, state: 'uploaded', uploaded_at: null, delivered_at: null,
  played_at: null, updated_at: '2026-09-20T18:04:31Z', ...over,
})

test('crc32 is the zlib one', () => {
  assert.equal(crc32(new TextEncoder().encode('123456789')), 0xcbf43926)
})

for (const v of VECTORS) {
  test(`vector: ${v.name}`, () => {
    const c = fromBytea(v.container_hex)
    assert.ok(crcOk(c))
    const h = parseHeader(c)
    assert.ok(!('error' in h))
    assert.deepEqual([h.codec, h.durationMs, h.sampleRate, h.keyId, h.flags & 1],
      [v.codec, v.duration_ms, v.sample_rate, v.key_id, 1])
    assert.equal(headerMatches(h, row({ codec: v.codec, duration_ms: v.duration_ms, key_id: v.key_id })), true)
  })
}

test('a flipped bit fails the crc; chunks reassemble to the same bytes', () => {
  const c = fromBytea(VECTORS[0].container_hex)
  const parts = [c.subarray(0, 10), c.subarray(10, 50), c.subarray(50)]
  assert.deepEqual(concat(parts), c)
  assert.deepEqual(fromBytea(toBytea(c)), c)
  const bad = c.slice()
  bad[30] ^= 1
  assert.equal(crcOk(bad), false)
})

test('an unencrypted container is refused', () => {
  const c = fromBytea(VECTORS[0].container_hex).slice()
  c[7] = 0
  const h = parseHeader(c)
  assert.ok(!('error' in h))
  assert.match(String(headerMatches(h, row())), /not encrypted/)
})

test('v1 routing: box → parent-a only, parents → box only', () => {
  const m = { seq: 1, to: 'parent-a', created_at: '2026-09-20T18:04:11Z', time_ok: true, duration_ms: 1000, codec: 2, key_id: 1, bytes: 100 }
  assert.ok(!('error' in validateMetadata('box', m)))
  assert.ok('error' in validateMetadata('box', { ...m, to: 'parent-b' }))
  assert.ok('error' in validateMetadata('parent-a', m))
  assert.ok(!('error' in validateMetadata('parent-a', { ...m, to: 'box', codec: 3 })))
  assert.ok('error' in validateMetadata('box', { ...m, duration_ms: 5 * 60 * 1000 + 1 }))
  assert.ok('error' in validateMetadata('box', { ...m, codec: 1 }))
})

test('the box token reaches its current inbox and nothing else', () => {
  const toBox = row({ sender: 'parent-a', recipient: 'box' })
  assert.equal(canFetchAudio('box', toBox), true)
  assert.equal(canFetchAudio('box', { ...toBox, state: 'delivered' }), true)
  assert.equal(canFetchAudio('box', { ...toBox, state: 'played' }), false)   // history
  assert.equal(canFetchAudio('box', row()), false)                           // its own sent message
  assert.equal(canFetchAudio('parent-a', row({ state: 'played' })), true)    // the archive
  assert.equal(canFetchAudio('parent-b', row()), false)                      // not a shared inbox
  assert.equal(canFetchAudio('parent-a', row({ state: 'uploading' })), false)
})

test('chunks', () => {
  assert.equal(chunkTotalFor(1), 1)
  assert.equal(chunkTotalFor(32768), 1)
  assert.equal(chunkTotalFor(32769), 2)
  assert.deepEqual(missingChunks([0, 1, 2, 5], 6), [3, 4])
})

test('range', () => {
  assert.equal(parseRange(null, 100), null)
  assert.deepEqual(parseRange('bytes=10-', 100), { start: 10, end: 99 })
  assert.deepEqual(parseRange('bytes=10-19', 100), { start: 10, end: 19 })
  assert.deepEqual(parseRange('bytes=-10', 100), { start: 90, end: 99 })
  assert.deepEqual(parseRange('bytes=90-500', 100), { start: 90, end: 99 })
  assert.equal(parseRange('bytes=100-', 100), 'unsatisfiable')
})

test('settings: no mute, limits enforced, who-set-what recorded', () => {
  const now = '2026-09-22T08:00:00Z'
  const ok = patchSettings('parent-a', DEFAULT_SETTINGS, {}, { poll: { backstop_minutes: 15 }, volume: 50 }, now)
  assert.ok('settings' in ok)
  assert.equal(ok.settings.poll.backstop_minutes, 15)
  assert.deepEqual(ok.changed, ['poll.backstop_minutes', 'volume'])
  assert.deepEqual(ok.meta['volume'], { by: 'parent-a', at: now })
  assert.equal(DEFAULT_SETTINGS.volume, 70)   // not mutated
  assert.ok(!('mute' in DEFAULT_SETTINGS))

  const mute = patchSettings('parent-a', DEFAULT_SETTINGS, {}, { mute: { a: true } }, now)
  assert.ok('status' in mute && mute.status === 403)   // there is no mute (ADR 0020)
  const box = patchSettings('box', DEFAULT_SETTINGS, {}, { volume: 1 }, now)
  assert.ok('status' in box && box.status === 403)
  const range = patchSettings('parent-a', DEFAULT_SETTINGS, {}, { poll: { idle_minutes: 120 } }, now)
  assert.ok('status' in range && range.status === 400)
  const unknown = patchSettings('parent-a', DEFAULT_SETTINGS, {}, { transcribe: true }, now)
  assert.ok('status' in unknown && unknown.status === 403)
  const same = patchSettings('parent-a', DEFAULT_SETTINGS, {}, { volume: 70 }, now)
  assert.ok('changed' in same && same.changed.length === 0)
})

test('cursor round-trips and rejects junk', () => {
  const c = encodeCursor('2026-09-20T18:04:31.123456+00:00', '01JAYZ3K7QW9E8RVX2M4N6P8TD')
  assert.deepEqual(decodeCursor(c), { updatedAt: '2026-09-20T18:04:31.123456+00:00', id: '01JAYZ3K7QW9E8RVX2M4N6P8TD' })
  assert.equal(decodeCursor('not a cursor'), null)
})

test('doorbell: the address is this project Realtime; no topic or key means none', () => {
  const d = doorbellFor('https://ref.supabase.co', 'pk+/=', 'doorbell:abc')
  assert.deepEqual(d, { url: 'wss://ref.supabase.co/realtime/v1/websocket?apikey=pk%2B%2F%3D&vsn=1.0.0', topic: 'doorbell:abc' })
  assert.equal(doorbellFor('https://ref.supabase.co', undefined, 'doorbell:abc'), null)
  assert.equal(doorbellFor('https://ref.supabase.co', 'k', null), null)
  assert.equal(doorbellFor('http://127.0.0.1:54321/', 'k', 't')!.url, 'ws://127.0.0.1:54321/realtime/v1/websocket?apikey=k&vsn=1.0.0')
})

test('settings: the backstop is a parent setting within 5-30 minutes', () => {
  const now = '2026-09-22T10:00:00Z'
  assert.equal(DEFAULT_SETTINGS.poll.backstop_minutes, 10)
  const ok = patchSettings('parent-a', DEFAULT_SETTINGS, {}, { poll: { backstop_minutes: 15 } }, now)
  assert.ok('settings' in ok && ok.settings.poll.backstop_minutes === 15)
  const bad = patchSettings('parent-a', DEFAULT_SETTINGS, {}, { poll: { backstop_minutes: 1 } }, now)
  assert.ok('status' in bad && bad.status === 400)
})
