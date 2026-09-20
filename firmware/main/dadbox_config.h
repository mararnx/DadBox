#pragma once

// Board: LILYGO T-SIM7080G-S3 (ADR 0012). Pins marked FIXED come from the
// LILYGO docs; everything else is PROVISIONAL — confirm against the board's
// pinout image before soldering. On this board GPIO 4-7, 10-13, 45, 46, 48
// are spoken for; 35-37 are the octal PSRAM; 19/20 are USB; 0/3/45/46 strap.

// Modem — SIM7080G on UART, esp_modem PPP. ADR 0006 / 0012.  (FIXED)
#define PIN_MODEM_TX     4
#define PIN_MODEM_RX     5
#define PIN_MODEM_RI     6
#define PIN_MODEM_DTR    7    // wake from PSM
#define PIN_MODEM_PWRKEY 46
#define PIN_MODEM_RTS    48
#define PIN_MODEM_CTS    45

// TF card — optional outbox overflow, ADR 0010.  (FIXED)
#define PIN_SD_CS       10
#define PIN_SD_MOSI     11
#define PIN_SD_SCK      12
#define PIN_SD_MISO     13

// I2C — PMU (AXP2101) on the PMU variant.  (FIXED)
#define PIN_I2C_SDA      3
#define PIN_I2C_SCL      2

// I2S in — MSM261S4030H0 / INMP441 microphone.  (provisional)
#define PIN_MIC_BCLK   14
#define PIN_MIC_WS     15
#define PIN_MIC_DIN    16
// No PIN_MIC_EN: the mic's VDD is switched by the lid's reed contact in
// hardware. Firmware only *reads* the lid (PIN_LID_SWITCH). ADR 0007.

// I2S out — MAX98357A amplifier.  (provisional)
#define PIN_AMP_BCLK   17
#define PIN_AMP_WS     18
#define PIN_AMP_DOUT   21
#define PIN_AMP_SD     38   // shutdown; low = off. Off unless playing or chiming.

// Controls — ADR 0007 / 0009.  (provisional)
#define PIN_LID_SWITCH 41   // reed contact: closed = lid closed. Same contact powers the mic.
#define PIN_BTN_PLAY   42   // the only button on the outside, through the side wall
#define PIN_BTN_LED    40   // the 33 mm button's own LED — lit while waiting
#define PIN_RING_DATA  39
#define PIN_RING_EN    47   // FET on the ring's supply. WS2812B draw ~1 mA each even dark.
#define LED_RING_PIXELS 16

// Status LEDs — the adults' channel, ADR 0009. Patterns, not colours.
#define PIN_LED_LINK    1
#define PIN_LED_POWER   8
#define STATUS_BLINK_MS      10     // short enough to be free and invisible at night
#define STATUS_PERIOD_MS     3000
#define RING_RESTING_AFTER_S (2 * 3600)   // waiting → resting; see ARCHITECTURE.md

// Battery sense — PMU variant: read the AXP2101 over I2C. Standard variant:
// ADC divider on a pin from the 1-21 range; assign once the board is in hand.
#define PIN_VBAT_SENSE  9   // Standard variant only, provisional

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
