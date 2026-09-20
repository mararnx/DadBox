# ADR 0002 — Cellular, not Wi-Fi

**Date:** 2026-09-20
**Status:** accepted

## Context

The box lives in the other parent's home. Wi-Fi setup there is not a technical
problem, it is a social one: it needs their password, their cooperation at
install time, and their cooperation again every time the router, ISP or
password changes. When it breaks, it breaks silently, in a house where nobody
has a reason to debug it — and the failure lands on a child who thinks the
messages stopped coming.

## Decision

Cellular. The box connects on its own and is never a guest on anyone's network.

Using a Blues Notecard (cellular) rather than a bare modem + SIM: the data plan
is bundled with the hardware, so there is no monthly bill, no carrier account,
and no SIM to source or activate. For a single family device, the higher parts
cost buys away the entire recurring-admin problem.

## Alternatives considered

- **Wi-Fi** — free and lower power, but see above. The failure mode is the
  project's whole reason for existing going quiet.
- **Bare LTE-M modem (SIM7080G) + third-party data SIM** — roughly half the
  hardware cost, but AT-command plumbing, carrier provisioning, and an account
  that can lapse. Wrong trade for one unit.
- **Wi-Fi with cellular failover** — best reliability, twice the work. Revisit
  only if cellular coverage at that address turns out to be poor.

## Consequences

- Bigger power budget: transmit bursts need a healthy LiPo and good decoupling.
  The box is mains-powered by default; the battery is for being carried around.
- Data is metered, so audio must be compressed. This is not a real constraint —
  see [ARCHITECTURE.md](../ARCHITECTURE.md).
- The box can be handed over working. Setup is plugging it in.
- Coverage at the destination address is now a hard dependency. **Verify it
  before ordering parts.**
