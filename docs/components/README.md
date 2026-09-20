# Components

One file per component. Each has the same shape: what it does, what is
currently decided, what was checked in the [review](../REVIEW.md), and the
questions that have to be answered before it can be built.

| Component | Stream | Decision-blocking questions |
| --- | --- | --- |
| [Audio capture](audio-capture.md) | firmware / hardware | gesture, cap, gating |
| [Audio playback](audio-playback.md) | firmware / hardware | volume control, chimes |
| [Codec](codec.md) | firmware | Opus vs ADPCM, where it runs |
| [Storage & queue](storage-queue.md) | firmware | retention on device, resume |
| [Connectivity](connectivity.md) | firmware / hardware | ~~module~~ decided; coverage, roaming |
| [Power](power.md) | hardware | ~~operate vs survive~~ decided; dock vs cable, thermal |
| [Controls & UI](controls-ui.md) | firmware / hardware | ~~lid or buttons~~ decided; brightness, haptics |
| [Enclosure](enclosure.md) | hardware | **lid mechanism**, form, acoustics |
| [Server](server.md) | server | hosting, auth, two parents |
| [iOS app](ios-app.md) | ios | two parents, alerts |
| [Security & privacy](security-privacy.md) | all | **on-device encryption in v1?**, key ceremony |

Bold questions are the next ones to answer; struck-through ones were decided
on 2026-09-20 — see each file's **Decided** note and [REVIEW.md](../REVIEW.md).
