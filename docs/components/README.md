# Components

One file per component. Each has the same shape: what it does, the current
design, what was checked and still holds, and the questions that are still
open. History and reasoning live in the [ADRs](../decisions/) and the
[review](../REVIEW.md); these files describe the design as it stands.

| Component | Stream | Open questions |
| --- | --- | --- |
| [Audio capture](audio-capture.md) | box / hardware | start chime, silence auto-stop, mic supply noise |
| [Audio playback](audio-playback.md) | box / hardware | volume, chime, replay, **grille and cavity** |
| [Codec](codec.md) | box | bitrate and trim thresholds, by ear |
| [Storage & queue](storage-queue.md) | box | inbox grace, update path, endurance card |
| [Connectivity](connectivity.md) | box / hardware | **power key, Ethernet-mode persistence**, which antenna, both bedrooms |
| [Power](power.md) | hardware | **measure first**; UPS module height, holder length, output blip |
| [Controls & UI](controls-ui.md) | box / hardware | **wall or top plate**, LED brightness at 3.3 V, status LED placement |
| [Enclosure](enclosure.md) | hardware | **measure the clone**, layout, grille, sturdier wiring |
| [Server](server.md) | server | which host, two parents |
| [iOS app](ios-app.md) | ios | two parents, alerts |
| [Security & privacy](security-privacy.md) | all | key ceremony, re-keying, the co-parent's page |

Bold questions are the next ones to answer — most of them with the parts in
hand.
