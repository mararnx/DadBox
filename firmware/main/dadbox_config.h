#pragma once

// Pin assignments are PROVISIONAL — confirm against the DevKitC-1 pinout and
// avoid the strapping pins (0, 3, 45, 46) before soldering anything.

// I2S in — ICS-43434 microphone
#define PIN_MIC_BCLK    4
#define PIN_MIC_WS      5
#define PIN_MIC_DIN     6

// I2S out — MAX98357A amplifier
#define PIN_AMP_BCLK   15
#define PIN_AMP_WS     16
#define PIN_AMP_DOUT    7

// Controls
#define PIN_BTN_RECORD  1
#define PIN_BTN_PLAY    2
#define PIN_LED_RING   18
#define LED_RING_PIXELS 16

// Notecard (phase 2)
#define PIN_I2C_SDA     8
#define PIN_I2C_SCL     9

// Audio — see docs/PROTOCOL.md. Changing these changes the wire format.
//
// KNOWN WRONG — docs/REVIEW.md §2. 300 s of raw 16-bit PCM is 9.6 MB and the
// board has 8 MB of PSRAM. Resolves with the gesture decision: a ~90 s hold cap
// fits raw; a 5-minute lid/toggle cap needs ADPCM in the capture path or
// streaming to flash. Do not build on this number until that is decided.
#define AUDIO_SAMPLE_RATE_HZ   16000
#define AUDIO_MAX_SECONDS      300
#define AUDIO_MAX_PCM_BYTES    (AUDIO_SAMPLE_RATE_HZ * 2 * AUDIO_MAX_SECONDS)  // ~9.6 MB — see above
