// APNs, directly — no Firebase, no relay (ADR 0017). Payloads carry a kind and
// ids, never content and never a name (PROTOCOL.md § Push).
//
// Secrets (function secrets, never the repo): APNS_KEY_P8, APNS_KEY_ID,
// APNS_TEAM_ID, APNS_TOPIC (the app's bundle id). Until they exist every push
// is a logged no-op, so the rest of the server works before the Apple account does.

export type PushKind = 'message' | 'played' | 'box_late' | 'fault' | 'battery_low' | 'unplayed_48h'
export type Device = { apns_token: string; environment: 'production' | 'sandbox' }
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
      ...(kind === 'message' ? { 'mutable-content': 1 } : {}),
      ...(passive ? { 'interruption-level': 'passive' } : { sound: kind === 'message' ? 'message.caf' : 'default' }),
    },
    kind,
    ...data,
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

export async function push(devices: Device[], kind: PushKind, data: Record<string, unknown> = {}): Promise<PushResult[]> {
  const p8 = Deno.env.get('APNS_KEY_P8'), keyId = Deno.env.get('APNS_KEY_ID')
  const teamId = Deno.env.get('APNS_TEAM_ID'), topic = Deno.env.get('APNS_TOPIC')
  if (!p8 || !keyId || !teamId || !topic) {
    console.log(`push skipped (APNs not configured): ${kind}`)
    return []
  }
  if (devices.length === 0) return []
  const jwt = await providerToken(p8, keyId, teamId)
  const background = kind === 'played'
  const body = JSON.stringify(payloadFor(kind, data))
  return await Promise.all(devices.map(async (d) => {
    const host = d.environment === 'production' ? 'api.push.apple.com' : 'api.sandbox.push.apple.com'
    try {
      const r = await fetch(`https://${host}/3/device/${d.apns_token}`, {
        method: 'POST',
        redirect: 'manual',
        headers: {
          authorization: `bearer ${jwt}`,
          'apns-topic': topic,
          'apns-push-type': background ? 'background' : 'alert',
          'apns-priority': background ? '5' : '10',
          // A box that was late an hour ago is not news; a message still is.
          'apns-expiration': String(Math.floor(Date.now() / 1000) + (kind === 'message' ? 7 * 86400 : 3600)),
          ...(typeof data.id === 'string' ? { 'apns-collapse-id': `${kind}:${data.id}` } : {}),
        },
        body,
      })
      if (!r.ok) console.error(`apns ${kind} → ${r.status} ${await r.text()}`)
      return { token: d.apns_token, status: r.status, gone: r.status === 410 }
    } catch (e) {
      console.error(`apns ${kind} failed: ${e}`)
      return { token: d.apns_token, status: 0, gone: false }
    }
  }))
}
