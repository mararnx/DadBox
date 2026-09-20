// DadBox firmware — skeleton.
//
// Read docs/ARCHITECTURE.md and docs/PROTOCOL.md before filling any of this in.
// The one rule that shapes everything: capture raw PCM while the button is
// held, and encode only after it is released. There is no real-time constraint
// on a voice message, and pretending there is makes the firmware hard.

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "dadbox_config.h"

static const char *TAG = "dadbox";

typedef enum {
    STATE_IDLE,          // ring dark
    STATE_WAITING,       // messages in the inbox — slow warm breathing, N segments
    STATE_RECORDING,     // ring fills toward the cap
    STATE_SENDING,       // one pulse, then back
    STATE_PLAYING,       // segment-by-segment progress
    STATE_SLEEPING,      // no link for a long time — honest, not alarming
} dadbox_state_t;

// There is deliberately no STATE_ERROR. Anything that goes wrong is a
// grown-up's problem and surfaces in the parent's app, never on the box.

static dadbox_state_t s_state = STATE_IDLE;

void app_main(void)
{
    ESP_LOGI(TAG, "DadBox starting");

    size_t psram = heap_caps_get_total_size(MALLOC_CAP_SPIRAM);
    ESP_LOGI(TAG, "PSRAM: %u bytes", (unsigned) psram);
    if (psram < AUDIO_MAX_PCM_BYTES) {
        // Not fatal — shorter recordings still work — but if this is 0 you have
        // the wrong board variant. See hardware/SHOPPING-LIST.md.
        ESP_LOGW(TAG, "PSRAM below the full-length buffer (%d bytes)", AUDIO_MAX_PCM_BYTES);
    }

    // M0 — the only milestone this file needs to reach first:
    //   TODO: audio_in_init()   I2S RX from the ICS-43434
    //   TODO: audio_out_init()  I2S TX to the MAX98357A
    //   TODO: ui_init()         buttons (debounced, hold-to-record) + LED ring
    //   Hold record -> capture to PSRAM. Release -> stop.
    //   Press play -> play that buffer back. Nothing else. No network, no flash.
    //
    // Only once that sounds good:
    //   TODO: codec_init()      encode after release, never during capture
    //   TODO: queue_init()      durable outbox/inbox in flash, survives power loss
    //   TODO: link_init()       Notecard over I2C, chunked upload, backoff
    //   TODO: quiet hours, mute, battery telemetry

    while (true) {
        switch (s_state) {
            case STATE_IDLE:
            default:
                break;
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
