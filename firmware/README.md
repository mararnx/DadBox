# Firmware

LILYGO T-SIM7080G-S3 — ESP32-S3 (N16R8) with the SIM7080G on board
([ADR 0012](../docs/decisions/0012-lilygo-t-sim7080g-s3.md)). ESP-IDF v5.x.

## Build

```bash
. $IDF_PATH/export.sh
idf.py set-target esp32s3
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
| `link` | `esp_modem` PPP on the SIM7080G, PWRKEY sequencing, PSM | no |
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
- The SIM7080G lives on the LILYGO board: UART on GPIO 4/5, PWRKEY 46,
  DTR 7. Level shifting and modem power are the board's problem, not ours.
- The mic's power is switched by the lid's reed contact in hardware. Firmware
  reads the lid; it never controls the mic rail.
- LILYGO ships two variants (PMU / Standard). Battery sensing differs — see
  `dadbox_config.h`.
