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
| [Connectivity](connectivity.md) | firmware / hardware | **Notecard vs bare modem**, latency |
| [Power](power.md) | hardware | **operate vs survive unplugged** |
| [Controls & UI](controls-ui.md) | firmware / hardware | **lid or buttons**, transport lock |
| [Enclosure](enclosure.md) | hardware | form, acoustics, drop |
| [Server](server.md) | server | hosting, auth, two parents |
| [iOS app](ios-app.md) | ios | two parents, alerts |
| [Security & privacy](security-privacy.md) | all | on-device encryption, key handling |

Bold questions gate the shopping list.
