// DadBox firmware — skeleton.
//
// Read docs/ARCHITECTURE.md and docs/PROTOCOL.md before filling any of this in.
// The rules that shape everything:
//   - The lid is the record gesture and the mic's power switch (ADR 0007).
//   - No real-time-constrained codec in the capture path. ADPCM as it goes is
//     fine; anything heavier happens after the lid closes.
//   - Every rail is gated. The target is a weekend on battery (ADR 0005).
//   - There is no error state. Faults go to the parent's app, never the ring.

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "dadbox_config.h"

static const char *TAG = "dadbox";

// The ring is the child's vocabulary (ADR 0009). Priority order, highest wins.
// It never shows link, battery or faults — there is deliberately no RING_ERROR.
typedef enum {
    RING_LISTENING,      // 1. lid open — steady, bright, never animated. The mic-is-on signal.
    RING_PLAYING,        // 2. progress sweep
    RING_GOT_IT,         // 3. lid just closed AND the message is fsynced — one pulse, ~600 ms
    RING_WAITING,        // 4. inbox > 0 — slow warm breathing, N segments; resting after 2 h
    RING_IDLE,           // 5. dark, ring rail off
} ring_state_t;

// The status LEDs are the adults' vocabulary. Off means fine.
typedef enum {
    LINK_OK,             // off
    LINK_DOWN,           // 1 blink / 3 s
    LINK_DOWN_QUEUED,    // 2 blinks / 3 s — messages waiting to go, safe on flash
} link_state_t;

typedef enum {
    PWR_OK,              // off
    PWR_CHARGING,        // steady
    PWR_LOW,             // 1 blink / 3 s, below BATTERY_LOW_PCT on battery
    PWR_ASLEEP,          // off; box asleep below BATTERY_SLEEP_PCT, lid does nothing
} power_state_t;

typedef enum {
    FAULT_NONE, FAULT_STORAGE, FAULT_MODEM, FAULT_CAPTURE, FAULT_CHARGER,
} fault_t;               // any non-NONE → LINK and POWER alternate

static ring_state_t  s_ring  = RING_IDLE;
static link_state_t  s_link  = LINK_DOWN;
static power_state_t s_power = PWR_OK;
static fault_t       s_fault = FAULT_NONE;

void app_main(void)
{
    ESP_LOGI(TAG, "DadBox starting");

    size_t psram = heap_caps_get_total_size(MALLOC_CAP_SPIRAM);
    ESP_LOGI(TAG, "PSRAM: %u bytes", (unsigned) psram);
    if (psram < AUDIO_ADPCM_BYTES) {
        // If this is 0 you have the wrong board variant (needs N16R8).
        // See hardware/SHOPPING-LIST.md.
        ESP_LOGW(TAG, "PSRAM below the full-length buffer (%d bytes)", AUDIO_ADPCM_BYTES);
    }

    // M0 — the only milestone this file needs to reach first. No network.
    //   TODO: ui_init()         lid switch (debounced), play button, ring behind PIN_RING_EN
    //   TODO: audio_in_init()   I2S RX from the ICS-43434; PIN_MIC_EN mirrors the lid
    //   TODO: adpcm             IMA-ADPCM encode in the I2S read loop → PSRAM
    //   TODO: audio_out_init()  I2S TX to the MAX98357A; PIN_AMP_SD high only while playing
    //   Lid open → capture. Lid close → trim, keep in PSRAM. Play → decode and play it.
    //
    // Only once that sounds good, in the cardboard box:
    //   TODO: queue_init()      LittleFS outbox/inbox, container + CRC, survives power loss
    //   TODO: link_init()       esp_modem PPP on the SIM7080G; PWRKEY sequence; PSM
    //   TODO: sync              chunked resumable upload, check-in, inbox download
    //   TODO: settings          quiet hours, mute, poll interval, brightness, volume
    //   TODO: power             light sleep between events; measure every rail

    // Durability (ADR 0010): the RING_GOT_IT pulse is only ever raised after the
    // outbox write has been fsynced. Never before. The outbox is never evicted.

    while (true) {
        switch (s_ring) {
            case RING_IDLE:
            default:
                break;
        }
        (void) s_link; (void) s_power; (void) s_fault;
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
