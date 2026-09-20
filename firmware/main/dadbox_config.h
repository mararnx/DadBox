#pragma once

// Board: LILYGO T-A7670G R2 — classic ESP32 (WROVER), A7670G LTE Cat-1.
// ADR 0013. Modem and TF pins are from the LILYGO/RandomNerd pinout and are
// marked FIXED; everything else is PROVISIONAL until the board is on the
// bench. WROVER: GPIO 6-11 are flash, 16/17 are PSRAM — never use them.
// 34-39 are input-only. 0/2/12/15 are strapping pins — inputs only, or avoid.

// Modem — A7670G on UART, esp_modem PPP.  (FIXED — LILYGO / RandomNerd pinout)
#define PIN_MODEM_TX       26
#define PIN_MODEM_RX       27
#define PIN_MODEM_PWRKEY    4
#define PIN_MODEM_DTR      25   // sleep/wake; the A7670 idles ~2 mA asleep
#define PIN_MODEM_RI       33
#define PIN_MODEM_RESET     5
#define PIN_MODEM_POWER_ON 12   // board-level modem supply enable; strapping pin, leave low at boot

// TF card — THE outbox (4 MB flash can't hold OTA + queue). ADR 0013.  (FIXED)
#define PIN_SD_SCK      14
#define PIN_SD_MISO      2
#define PIN_SD_MOSI     15
#define PIN_SD_CS       13

// Battery — on-board divider.  (FIXED)
#define PIN_VBAT_SENSE  35   // ADC1_CH7, input-only

// --- Pin budget -------------------------------------------------------------
// After the fixed pins, a WROVER has six free native outputs (18 19 21 22 23 32)
// and three free input-only pins (34 36 39). That is exactly enough if the mic
// and the amp SHARE one I2S port in full-duplex (common BCLK + WS, separate
// DIN/DOUT) — they never run at different rates and never both at once anyway.

// I²C — PCF8574 expander for the slow outputs.  (provisional)
#define PIN_I2C_SDA     21
#define PIN_I2C_SCL     22
#define PCF8574_ADDR    0x20
//   P0 LED_LINK   P1 LED_POWER   P2 RING_EN   P3 AMP_SD   P4 BTN_LED   P5-P7 spare

// I2S — ONE port, full duplex. Mic RX and amp TX share the clocks.  (provisional)
#define PIN_I2S_BCLK   18
#define PIN_I2S_WS     19
#define PIN_I2S_DOUT   23   // → MAX98357A DIN
#define PIN_I2S_DIN    34   // ← MSM261S4030H0 / INMP441 SD (input-only pin is fine)
// No PIN_MIC_EN: the mic's VDD is switched by the lid's reed contact in
// hardware. Firmware only *reads* the lid. ADR 0007.

// Ring — data on a native pin; its supply gate is on the expander.  (provisional)
#define PIN_RING_DATA  32
#define LED_RING_PIXELS 16

// Lid and play button — native input-only pins so they can wake the ESP32 and
// raise interrupts. Input-only pins have NO internal pull-ups: add 10 kΩ external.
#define PIN_LID_SWITCH 36   // reed contact: closed = lid closed. Same contact powers the mic.
#define PIN_BTN_PLAY   39   // the only button on the outside, through the side wall

// Status LEDs, ring gate, amp shutdown, button LED: on the expander (see above). ADR 0009.
#define STATUS_BLINK_MS      10
#define STATUS_PERIOD_MS     3000
#define RING_RESTING_AFTER_S (2 * 3600)

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
