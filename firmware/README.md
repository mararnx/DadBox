# Firmware

LILYGO T-A7670G R2 — classic ESP32 (WROVER, 4 MB flash, 8 MB PSRAM) with the
A7670G LTE Cat-1 modem on board ([ADR 0013](../docs/decisions/0013-cat1-not-catm.md)).
ESP-IDF v5.x.

## Build

```bash
. $IDF_PATH/export.sh
idf.py set-target esp32
idf.py build flash monitor
```

## Shape of it

| Module | Job | Exists |
| --- | --- | --- |
| `ui` | Lid switch, play button, ring (gated), chimes, quiet hours, mute | no |
| `audio_in` | I2S capture while the lid is open; mic rail follows the lid | no |
| `adpcm` | IMA-ADPCM in the capture loop → PSRAM. Cheap enough to not count as real-time | no |
| `audio_out` | I2S playback through the amp; amp rail only while playing | no |
| `queue` | LittleFS outbox/inbox, container + CRC, survives power loss | no |
| `link` | `esp_modem` PPP on the A7670G, PWRKEY sequencing, DTR sleep | no |
| `sync` | Resumable 32 KB chunk upload, check-in, inbox download | no |
| `power` | Light/deep sleep, rail gating, battery sense | no |
| `codec` | Opus transcode after the lid closes — M3 | no |

## First target — M0

Open lid (a toggle switch on the bench) → talk → close → press play → hear it.
No network, no flash. It proves the mic, the amp, ADPCM, the PSRAM buffer and
the gating in one go, and it is the cheapest possible way to find out the
audio quality is bad. Listen to it inside a cardboard box, not on the bench.

Do not buy the modem until this sounds good.

## Notes

- Pin assignments in `main/dadbox_config.h` are provisional — check the
  strapping pins before soldering.
- Wire format lives in [../docs/PROTOCOL.md](../docs/PROTOCOL.md). Change it
  there first.
- The A7670G lives on the LILYGO board: UART on GPIO 26/27, PWRKEY 4,
  DTR 25. Level shifting and modem power are the board's problem, not ours.
- **The outbox is on the TF card**, not internal flash — 4 MB is OTA and NVS
  only. Mount with sync-on-write; a missing card is a fault, never a silent
  drop. Internal flash keeps the most recent message as a fallback.
- The mic's power is switched by the lid's reed contact in hardware. Firmware
  reads the lid; it never controls the mic rail.
- The WROVER is short on pins after the modem and TF: slow signals go through
  a PCF8574 on I²C — see `dadbox_config.h`.
