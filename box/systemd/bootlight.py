#!/usr/bin/python3
"""The power-on rainbow on Play, from early boot until the service's light driver
takes the pins (ADR 0024 §7). Runs on the system Python from the root, not the
venv on /data: /data is not mounted this early. Stops when the driver creates
/run/dadbox/bootlight-stop. Keep EQUAL and the period in step with lights.py."""
import os
import time

import lgpio

PINS = (23, 24, 25)                  # Play red, green, blue
EQUAL = (0.3, 0.25, 1.0)             # red, green, blue duties that look equally bright (lights.RAINBOW_EQUAL)
PERIOD_S = 4.5
STOP = "/run/dadbox/bootlight-stop"
FREQ = 1000                          # brief, at boot: finer than the service's 200 Hz, CPU no matter

h = lgpio.gpiochip_open(0)
for p in PINS:
    lgpio.gpio_claim_output(h, p, 0)
t0 = time.monotonic()
try:
    while not os.path.exists(STOP):
        # lights.rainbow: an even crossfade between equally bright primaries, so the
        # brightness holds and only the colour moves.
        x = ((time.monotonic() - t0) / PERIOD_S) % 1.0 * 3
        i, f = int(x) % 3, x - int(x)
        c = [0.0, 0.0, 0.0]
        c[i] = (1 - f) * EQUAL[i]
        c[(i + 1) % 3] = f * EQUAL[(i + 1) % 3]
        for p, v in zip(PINS, c):
            lgpio.tx_pwm(h, p, FREQ, 100.0 * v)
        time.sleep(1 / 60)
finally:
    for p in PINS:
        lgpio.tx_pwm(h, p, FREQ, 0)
        lgpio.gpio_write(h, p, 0)
        lgpio.gpio_free(h, p)
    lgpio.gpiochip_close(h)
