# Firmware

ESP32-S3 (N16R8). ESP-IDF.

Nothing here yet. See [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for
the audio path and state machine before writing any of it.

## Planned modules

| Module | Job |
| --- | --- |
| `audio_in` | I2S capture to a PSRAM ring buffer while record is held |
| `audio_out` | I2S playback through the amp |
| `codec` | Encode after release — never in the capture path |
| `queue` | Durable outbox/inbox in flash; survives power loss |
| `link` | Notecard I2C, sync, chunked upload, backoff |
| `ui` | Buttons, LED ring, chimes, quiet hours |

## First target (M0)

Hold button → record → release → press play → hear it back. No network at all.
Proves the mic, the amp, the buffer and the buttons in one go.
