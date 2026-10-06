#!/usr/bin/python3
"""The power-on rainbow on Play, from early boot until the service's light driver
takes the pins (ADR 0024 §7). Runs on the system Python from the root, not the
venv on /data: /data is not mounted this early. Stops when the driver creates
/run/dadbox/bootlight-stop. Keep BALANCE and the period in step with lights.py."""
import colorsys
import os
import time

import lgpio

PINS = (23, 24, 25)                  # Play red, green, blue
BALANCE = (0.25, 0.63, 1.0)          # white on these buttons, tuned on the bench 2026-10-06
PERIOD_S = 3.0
STOP = "/run/dadbox/bootlight-stop"
FREQ = 200

h = lgpio.gpiochip_open(0)
for p in PINS:
    lgpio.gpio_claim_output(h, p, 0)
t0 = time.monotonic()
try:
    while not os.path.exists(STOP):
        c = colorsys.hsv_to_rgb(((time.monotonic() - t0) / PERIOD_S) % 1.0, 1.0, 1.0)
        m = [c[i] * BALANCE[i] for i in range(3)]
        top = max(m)
        for p, v in zip(PINS, m):
            lgpio.tx_pwm(h, p, FREQ, 100.0 * v / top)
        time.sleep(0.05)
finally:
    for p in PINS:
        lgpio.tx_pwm(h, p, FREQ, 0)
        lgpio.gpio_write(h, p, 0)
        lgpio.gpio_free(h, p)
    lgpio.gpiochip_close(h)
