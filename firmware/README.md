# Firmware

ESP32-S3 (N16R8), ESP-IDF v5.x.

## Build

```bash
. $IDF_PATH/export.sh
idf.py set-target esp32s3
idf.py build flash monitor
```

## Shape of it

| Module | Job | Exists |
| --- | --- | --- |
| `audio_in` | I2S capture to a PSRAM buffer while record is held | no |
| `audio_out` | I2S playback through the amp | no |
| `codec` | Encode *after* release — never in the capture path | no |
| `queue` | Durable outbox/inbox in flash, survives power loss | no |
| `link` | Notecard I2C, sync, chunked upload, backoff | no |
| `ui` | Buttons, LED ring, chimes, quiet hours | no |

## First target — M0

Hold record → talk → release → press play → hear it. No network, no flash, no
codec. It proves the mic, the amp, the PSRAM buffer and the buttons in one go,
and it is the cheapest possible way to find out the audio quality is bad.

Do not buy the cellular parts until this sounds good.

## Notes

- Pin assignments in `main/dadbox_config.h` are provisional — check the
  strapping pins before soldering.
- Wire format lives in [../docs/PROTOCOL.md](../docs/PROTOCOL.md). Change it
  there first.
