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

typedef enum {
    STATE_IDLE,          // ring dark, everything gated off
    STATE_WAITING,       // inbox non-empty — slow warm breathing, N segments
    STATE_LISTENING,     // lid open — mic powered, steady light, no timer
    STATE_SENT,          // lid just closed — one pulse, then back
    STATE_PLAYING,       // segment-by-segment progress
    STATE_SLEEPING,      // no link for a long time — very slow, very dim. Not "broken".
} dadbox_state_t;

// Deliberately no STATE_ERROR.

static dadbox_state_t s_state = STATE_IDLE;

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

    while (true) {
        switch (s_state) {
            case STATE_IDLE:
            default:
                break;
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
