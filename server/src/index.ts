// DadBox backend — skeleton.
//
// Smallest thing that can hold audio blobs and wake a phone. See
// ../docs/PROTOCOL.md; change the contract there before changing it here.
//
// This stream is NOT blocked by hardware. Build it against the fake box in
// tools/ so that the day the parts arrive, only the firmware is unknown.

import Fastify from 'fastify'

const app = Fastify({ logger: true })

// --- Messages ---------------------------------------------------------------

// Upload a message. `id` is a ULID minted by the *recording* end and is the
// idempotency key: a device that loses its uplink mid-upload will retry, and
// retries must not create duplicates.
app.post('/messages/:id', async (_req, reply) => {
  // TODO: auth, size cap, dedupe on id, store blob, enqueue for the recipient,
  //       APNs push if the recipient is the parent.
  return reply.code(501).send({ error: 'not implemented' })
})

app.get('/messages', async (_req, reply) => {
  // TODO: list undelivered messages for the caller.
  return reply.code(501).send({ error: 'not implemented' })
})

app.get('/messages/:id/audio', async (_req, reply) => {
  return reply.code(501).send({ error: 'not implemented' })
})

app.post('/messages/:id/played', async (_req, reply) => {
  // Starts the retention clock. See PROTOCOL.md § Retention.
  return reply.code(501).send({ error: 'not implemented' })
})

// --- Device -----------------------------------------------------------------

// Notehub route target. Inbound chunks from the box land here.
app.post('/notehub/inbound', async (_req, reply) => {
  // TODO: verify the route secret, reassemble chunks, complete the message.
  return reply.code(501).send({ error: 'not implemented' })
})

// Battery, signal, queue depth, firmware version — everything the parent app
// needs to distinguish "quiet" from "dead in a bag".
app.post('/device/telemetry', async (_req, reply) => {
  return reply.code(501).send({ error: 'not implemented' })
})

app.get('/device/state', async (_req, reply) => {
  return reply.code(501).send({ error: 'not implemented' })
})

// --- Controls ---------------------------------------------------------------

// Mute is settable by either household and visible to both. Quiet hours are
// enforced on the device, not by the sender's discipline.
app.put('/settings', async (_req, reply) => {
  return reply.code(501).send({ error: 'not implemented' })
})

app.get('/health', async () => ({ ok: true }))

const port = Number(process.env.PORT ?? 8080)
app.listen({ port, host: '0.0.0.0' })
