// APNs, directly — no Firebase, no relay (ADR 0017). Payloads carry a kind and
// ids, never content and never a name (PROTOCOL.md § Push).
//
// Secrets (function secrets, never the repo): APNS_KEY_P8, APNS_KEY_ID,
// APNS_TEAM_ID, APNS_TOPIC (the app's bundle id). Until they exist every push
// is a logged no-op, so the rest of the server works before the Apple account does.

export type PushKind = 'message' | 'played' | 'box_late' | 'fault' | 'battery_low' | 'unplayed_48h'
export type Device = { apns_token: string; environment: 'production' | 'sandbox'; live_activity_token?: string | null }
export type PushResult = { token: string; status: number; gone: boolean }

const ALERT_TEXT: Record<Exclude<PushKind, 'played'>, string> = {
  message: 'New message',          // retitled on the phone; the server never learns a name
  box_late: 'The box has gone quiet',
  fault: 'The box reports a problem',
  battery_low: 'Box battery is low',
  unplayed_48h: 'A message has not been played yet',
}

export function payloadFor(kind: PushKind, data: Record<string, unknown>) {
  if (kind === 'played') return { aps: { 'content-available': 1 }, kind, ...data }
  const passive = kind === 'battery_low' || kind === 'unplayed_48h'
  return {
    aps: {
      alert: { body: ALERT_TEXT[kind] },
      // A message is the one thing allowed through a Focus (ADR 0027). Without the app's
      // entitlement iOS delivers it as `active`, so the server may be ahead of the app.
      ...(kind === 'message' ? { 'mutable-content': 1, 'interruption-level': 'time-sensitive' } : {}),
      ...(passive ? { 'interruption-level': 'passive' } : { sound: kind === 'message' ? 'message.caf' : 'default' }),
    },
    kind,
    ...data,
  }
}

// The lock screen's "message waiting" (PROTOCOL.md § Live Activity, ADR 0027). An id and a
// second; the phone counts the minutes. `attributes-type` is the Swift type's name.
export function activityStartPayload(id: string, sinceS: number, nowS: number) {
  return {
    aps: {
      timestamp: nowS,
      event: 'start',
      'attributes-type': 'WaitingAttributes',
      attributes: { id },
      'content-state': { since: sinceS },
      alert: { title: 'New message', body: 'Waiting to be heard' },     // required by a start; no sound, the push has it
    },
  }
}

const b64url = (b: Uint8Array | string) =>
  btoa(typeof b === 'string' ? b : String.fromCharCode(...b))
    .replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')

let cachedJwt: { token: string; at: number } | null = null

// ES256 provider token; Apple wants it reused for 20–60 minutes, not minted per push.
async function providerToken(p8: string, keyId: string, teamId: string): Promise<string> {
  const now = Math.floor(Date.now() / 1000)
  if (cachedJwt && now - cachedJwt.at < 40 * 60) return cachedJwt.token
  const der = Uint8Array.from(atob(p8.replace(/-----[^-]+-----|\s/g, '')), (c) => c.charCodeAt(0))
  const key = await crypto.subtle.importKey('pkcs8', der, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign'])
  const head = b64url(JSON.stringify({ alg: 'ES256', kid: keyId }))
  const body = b64url(JSON.stringify({ iss: teamId, iat: now }))
  const sig = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, key, new TextEncoder().encode(`${head}.${body}`))
  cachedJwt = { token: `${head}.${body}.${b64url(new Uint8Array(sig))}`, at: now }
  return cachedJwt.token
}

type Apns = { p8: string; keyId: string; teamId: string; topic: string }

function configured(what: string): Apns | null {
  const p8 = Deno.env.get('APNS_KEY_P8'), keyId = Deno.env.get('APNS_KEY_ID')
  const teamId = Deno.env.get('APNS_TEAM_ID'), topic = Deno.env.get('APNS_TOPIC')
  if (p8 && keyId && teamId && topic) return { p8, keyId, teamId, topic }
  console.log(`push skipped (APNs not configured): ${what}`)
  return null
}

async function send(
  what: string, jwt: string, environment: Device['environment'], token: string,
  headers: Record<string, string>, body: string,
): Promise<PushResult> {
  const host = environment === 'production' ? 'api.push.apple.com' : 'api.sandbox.push.apple.com'
  try {
    const r = await fetch(`https://${host}/3/device/${token}`, {
      method: 'POST',
      redirect: 'manual',
      headers: { authorization: `bearer ${jwt}`, ...headers },
      body,
    })
    if (!r.ok) console.error(`apns ${what} → ${r.status} ${await r.text()}`)
    return { token, status: r.status, gone: r.status === 410 }
  } catch (e) {
    console.error(`apns ${what} failed: ${e}`)
    return { token, status: 0, gone: false }
  }
}

export async function push(devices: Device[], kind: PushKind, data: Record<string, unknown> = {}): Promise<PushResult[]> {
  const apns = configured(kind)
  if (!apns || devices.length === 0) return []
  const jwt = await providerToken(apns.p8, apns.keyId, apns.teamId)
  const background = kind === 'played'
  const body = JSON.stringify(payloadFor(kind, data))
  return await Promise.all(devices.map((d) =>
    send(kind, jwt, d.environment, d.apns_token, {
      'apns-topic': apns.topic,
      'apns-push-type': background ? 'background' : 'alert',
      'apns-priority': background ? '5' : '10',
      // A box that was late an hour ago is not news; a message still is.
      'apns-expiration': String(Math.floor(Date.now() / 1000) + (kind === 'message' ? 7 * 86400 : 3600)),
      ...(typeof data.id === 'string' ? { 'apns-collapse-id': `${kind}:${data.id}` } : {}),
    }, body)))
}

// How long iOS keeps a Live Activity running. A start that arrives later than this is not shown.
export const ACTIVITY_LIFE_S = 8 * 3600

// Starts the "message waiting" Live Activity on every device that gave a push-to-start token.
// `token` in each result is that live-activity token, not the device token.
export async function startActivity(devices: Device[], id: string, sinceS: number): Promise<PushResult[]> {
  const apns = configured('live activity')
  const able = devices.filter((d) => d.live_activity_token)
  if (!apns || able.length === 0) return []
  const jwt = await providerToken(apns.p8, apns.keyId, apns.teamId)
  const nowS = Math.floor(Date.now() / 1000)
  const body = JSON.stringify(activityStartPayload(id, sinceS, nowS))
  return await Promise.all(able.map((d) =>
    send('live activity', jwt, d.environment, d.live_activity_token!, {
      'apns-topic': `${apns.topic}.push-type.liveactivity`,
      'apns-push-type': 'liveactivity',
      'apns-priority': '10',
      'apns-expiration': String(sinceS + ACTIVITY_LIFE_S),
    }, body)))
}
