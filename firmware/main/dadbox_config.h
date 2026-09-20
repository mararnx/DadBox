#pragma once

// Pin assignments are PROVISIONAL — confirm against the DevKitC-1 pinout and
// avoid the strapping pins (0, 3, 45, 46) and the onboard RGB LED (38 or 48,
// revision-dependent) before soldering anything.

// I2S in — ICS-43434 microphone
#define PIN_MIC_BCLK    4
#define PIN_MIC_WS      5
#define PIN_MIC_DIN     6
#define PIN_MIC_EN     12   // load switch: mic VDD. Driven by the lid, mirrored here for state.

// I2S out — MAX98357A amplifier
#define PIN_AMP_BCLK   15
#define PIN_AMP_WS     16
#define PIN_AMP_DOUT    7
#define PIN_AMP_SD     14   // shutdown; low = off. Off unless playing or chiming.

// Controls — ADR 0007
#define PIN_LID_SWITCH 11   // open = recording. On the bench: a toggle switch.
#define PIN_BTN_PLAY    2   // the only button on the outside
#define PIN_RING_DATA  10
#define PIN_RING_EN    13   // FET on the ring's 5 V. WS2812B draw ~1 mA each even dark.
#define LED_RING_PIXELS 16

// Status LEDs — the adults' channel, ADR 0009. Patterns, not colours.
// Avoid 19/20 (USB), 35-37 (octal PSRAM), 38/48 (onboard RGB), 45/46 (strap).
#define PIN_LED_LINK   47
#define PIN_LED_POWER  21
#define STATUS_BLINK_MS      10     // short enough to be free and invisible at night
#define STATUS_PERIOD_MS     3000
#define RING_RESTING_AFTER_S (2 * 3600)   // waiting → resting; see ARCHITECTURE.md

// Modem — SIM7080G over UART, esp_modem PPP. ADR 0006.
// The module's UART is 1.8 V logic; the breakout MUST level-shift.
#define PIN_MODEM_TX   17
#define PIN_MODEM_RX   18
#define PIN_MODEM_PWRKEY 40
#define PIN_MODEM_DTR  41   // wake from PSM
#define PIN_MODEM_STATUS 42

// Power
#define PIN_VBAT_SENSE  9   // ADC, through a divider
#define PIN_CHG_STAT    8   // charger status

// Audio — see docs/PROTOCOL.md. Changing these changes the wire format.
#define AUDIO_SAMPLE_RATE_HZ   16000
#define AUDIO_MAX_SECONDS      300
// Capture is IMA-ADPCM as it goes (4 bits/sample), so the buffer is ~2.4 MB
// for the full cap — comfortably inside 8 MB PSRAM. Raw PCM would be 9.6 MB
// and would not fit; see docs/REVIEW.md §2 and ADR 0007.
#define AUDIO_ADPCM_BYTES      (AUDIO_SAMPLE_RATE_HZ * AUDIO_MAX_SECONDS / 2)
#define AUDIO_MIN_SPEECH_MS    1000   // shorter than this after trimming → discarded
#define AUDIO_MIC_SETTLE_MS    100    // discard after power-up; the mic clicks

// Protocol
#define UPLOAD_CHUNK_BYTES     (32 * 1024)
#define CHECKIN_DEFAULT_MIN    10

// Durability — ADR 0010. The outbox is never evicted.
#define CAPTURE_CHECKPOINT_S   30     // PSRAM → flash during capture
#define OUTBOX_FAULT_PCT       80     // fault pattern on the status LEDs above this
#define BATTERY_SLEEP_PCT      5      // below this the box sleeps and the lid does nothing
#define BATTERY_LOW_PCT        20
