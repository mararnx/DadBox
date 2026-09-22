// The DBX1 container, as far as the server may know it: header and crc32.
// There is no key in this file or anywhere on the server (ADR 0017) — the
// payload is ciphertext and stays that way.
//
// Framework-free: runs under Deno (the Edge Function) and Node (the tests).

export const HEADER_LEN = 16
export const FLAG_ENCRYPTED = 0x01
// header + key_id + nonce + tag + crc32: an encrypted message of zero bytes
export const MIN_CONTAINER_LEN = HEADER_LEN + 1 + 12 + 16 + 4

export type Header = {
  version: number
  codec: number
  channels: number
  flags: number
  sampleRate: number
  durationMs: number
  keyId: number
}

const TABLE = (() => {
  const t = new Uint32Array(256)
  for (let n = 0; n < 256; n++) {
    let c = n
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    t[n] = c >>> 0
  }
  return t
})()

export function crc32(bytes: Uint8Array, seed = 0): number {
  let c = ~seed >>> 0
  for (let i = 0; i < bytes.length; i++) c = TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8)
  return ~c >>> 0
}

export function parseHeader(container: Uint8Array): Header | { error: string } {
  if (container.length < MIN_CONTAINER_LEN) return { error: 'too short to be a container' }
  if (String.fromCharCode(...container.subarray(0, 4)) !== 'DBX1') return { error: 'bad magic' }
  const v = new DataView(container.buffer, container.byteOffset, container.byteLength)
  const header: Header = {
    version: v.getUint8(4),
    codec: v.getUint8(5),
    channels: v.getUint8(6),
    flags: v.getUint8(7),
    sampleRate: v.getUint32(8, true),
    durationMs: v.getUint32(12, true),
    keyId: v.getUint8(HEADER_LEN),
  }
  if (header.version !== 1) return { error: `unknown version ${header.version}` }
  return header
}

export function crcOk(container: Uint8Array): boolean {
  if (container.length < MIN_CONTAINER_LEN) return false
  const v = new DataView(container.buffer, container.byteOffset, container.byteLength)
  return crc32(container.subarray(0, container.length - 4)) === v.getUint32(container.length - 4, true)
}

export function concat(parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0))
  let at = 0
  for (const p of parts) {
    out.set(p, at)
    at += p.length
  }
  return out
}

// Postgres bytea over PostgREST travels as "\x…" hex.
export function toBytea(bytes: Uint8Array): string {
  let s = '\\x'
  for (let i = 0; i < bytes.length; i++) s += bytes[i].toString(16).padStart(2, '0')
  return s
}

export function fromBytea(hex: string): Uint8Array {
  const h = hex.startsWith('\\x') ? hex.slice(2) : hex
  const out = new Uint8Array(h.length / 2)
  for (let i = 0; i < out.length; i++) out[i] = parseInt(h.substr(i * 2, 2), 16)
  return out
}
