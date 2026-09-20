// DadBox backend — skeleton.
//
// Smallest thing that can hold audio blobs, wake a phone, and know whether the
// box is alive. See ../docs/PROTOCOL.md; change the contract there before
// changing it here.
//
// This stream is NOT blocked by hardware. Build it against tools/fakebox so
// that the day the parts arrive, only the firmware is unknown.

import Fastify from 'fastify'

const app = Fastify({ logger: true })

// Identities — ADR 0008. parent-b is reserved: the protocol knows about it,
// v1 does not implement it. Nothing below should assume there is only one.
type Identity = 'box' | 'parent-a' | 'parent-b'

// --- Messages: upload --------------------------------------------------------
// `id` is a ULID minted by the *recording* end and is the idempotency key. A
// device that loses its uplink mid-upload will retry; retries must not create
// duplicates. The server never mints ids.

app.put('/messages/:id', async (_req, reply) => {
  // TODO: auth → Identity; validate metadata; enforce `to` (v1: box → parent-a
  //       only); idempotent create; 200 if it already exists with same metadata.
  return reply.code(501).send({ error: 'not implemented' })
})

app.put('/messages/:id/chunks/:seq', async (_req, reply) => {
  // TODO: raw body, 32 KB max; header X-Chunk-Total; store idempotently by seq.
  return reply.code(501).send({ error: 'not implemented' })
})

app.get('/messages/:id/upload-state', async (_req, reply) => {
  // TODO: → { received: number[] } so the box can resume from the gaps on boot.
  return reply.code(501).send({ error: 'not implemented' })
})

app.post('/messages/:id/complete', async (_req, reply) => {
  // TODO: assemble, verify crc32 from the container trailer, mark uploaded,
  //       enqueue for recipient, APNs push if recipient is a parent.
  return reply.code(501).send({ error: 'not implemented' })
})

// --- Messages: download ------------------------------------------------------

app.get('/messages/:id/audio', async (_req, reply) => {
  // TODO: Range support — the box downloads over a link that drops.
  return reply.code(501).send({ error: 'not implemented' })
})

app.post('/messages/:id/played', async (_req, reply) => {
  // Starts the 24 h retention clock. See PROTOCOL.md § Retention.
  return reply.code(501).send({ error: 'not implemented' })
})

// --- Device ------------------------------------------------------------------

// The one request the box makes between events. Telemetry in, settings and
// inbox summary out. Battery, signal, queue depth, lid state, firmware — all
// of it is what lets the parent app tell "quiet" from "dead in a bag".
app.post('/device/checkin', async (_req, reply) => {
  // TODO: store telemetry with timestamp → { settings, inbox: string[] }.
  //       The "no check-in for N hours" alert is derived from the timestamp.
  return reply.code(501).send({ error: 'not implemented' })
})

app.get('/device/state', async (_req, reply) => {
  // For the app's Box screen: last telemetry + last check-in time.
  return reply.code(501).send({ error: 'not implemented' })
})

// --- Settings ----------------------------------------------------------------
// Mute is per household and visible to both. Quiet hours are enforced on the
// device, not by the sender's discipline. Poll interval is the latency/battery
// trade and belongs to the parent.
app.get('/settings', async (_req, reply) => {
  return reply.code(501).send({ error: 'not implemented' })
})

app.put('/settings', async (_req, reply) => {
  return reply.code(501).send({ error: 'not implemented' })
})

app.get('/health', async () => ({ ok: true }))

const port = Number(process.env.PORT ?? 8080)
app.listen({ port, host: '0.0.0.0' })
