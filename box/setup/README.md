# Box setup — what Claude does over SSH after the first boot

1. **Packages**: `ffmpeg alsa-utils python3-venv python3-lgpio i2c-tools` and Tailscale
   (`curl -fsSL https://tailscale.com/install.sh | sh`, then `tailscale up`
   — the auth link is the user's to open).
2. **`/boot/firmware/config.txt`**
   Change `dtparam=audio=on` to `off`, and append — comments on their own
   lines only; `config.txt` does not allow a comment after a value:
   ```
   # I2S mic + MAX98357A amp: GPIO 18/19/20/21; the driver owns GPIO 16 (amp SD_MODE). Do not also load max98357a.
   dtoverlay=googlevoicehat-soundcard
   # INA219 on the UPS Module 3S, later
   dtparam=i2c_arm=on
   dtparam=watchdog=on
   # serial console on GPIO 14/15 for the debug probe; no Bluetooth, so the full UART goes there
   enable_uart=1
   dtoverlay=disable-bt
   # in the field only; the bench needs Wi-Fi
   #dtoverlay=disable-wifi
   ```
   Plus, outside `config.txt`: `echo i2c-dev | sudo tee /etc/modules-load.d/i2c-dev.conf`
   (the `/dev/i2c-1` node), and the hardware watchdog armed by systemd:
   `/etc/systemd/system.conf.d/watchdog.conf` with `[Manager]` / `RuntimeWatchdogSec=15`.
3. **`/data`**: a second ext4 partition on the SD card, `noatime`, mounted
   by label. `/opt/dadbox` → symlink into `/data/app`. Raspberry Pi OS grows
   the root partition to fill the card on first boot, so the partition has
   to be made before that (or the card re-flashed). On the bench, `/data` is
   a plain directory on the root filesystem (2026-09-24).
4. **Overlay**: `raspi-config nonint enable_overlayfs` — after everything else
   is installed. Disable it only on the bench, never in the field.
5. **Service**, which runs as its own user, not root:
   ```
   sudo useradd --system --home /data --shell /usr/sbin/nologin \
        --groups gpio,audio,i2c,dialout dadbox
   sudo chown -R dadbox:dadbox /data
   echo 'dadbox ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff' | sudo tee /etc/sudoers.d/dadbox
   sudo chmod 0440 /etc/sudoers.d/dadbox && sudo visudo -c
   ```
   `python3 -m venv --system-site-packages /opt/dadbox/.venv` (so gpiozero
   finds apt's `lgpio`, which pip would have to compile), `pip install -e .[pi]`, the unit from
   `systemd/`, `systemctl enable --now dadbox`. `dadboxctl` on `$PATH`.
   Before the first start: `/data/config.env` with `DADBOX_URL` and
   `DADBOX_TOKEN`, and the family key in `/data/keys/1.key` (64 hex
   characters) — both **owned by `dadbox`, mode 0600**, or the service cannot
   read them. See `store.py` for the layout. Without them the service runs,
   records and queues, and cannot send.
   The watchdog keepalive needs no package: `dadbox/sdnotify.py` speaks
   systemd's notify socket directly (a venv cannot see apt's python3-systemd).
   The sudoers line allows one command, the clean shutdown below 5 % battery.
6. **Modem** (SIM7670G HAT on the Zero's OTG port). It enumerates as
   Qualcomm `05c6:9330`, not SIMCom's ID: `usb0` (RNDIS, the modem's own
   192.168.0.1 gateway) and AT ports `/dev/ttyACM0`–`3` (cdc_acm, AT on
   `ttyACM0`). `sudo python3 setup/modem_check.py --apn internet` reports SIM,
   registration, band and data through `usb0` only. Once per modem: the APN,
   then `AT+DIALMODE=0` (auto-dial; at `1` the modem registers and gets an
   address but forwards nothing) and `AT$MYCONFIG="usbnetmode",0` (RNDIS),
   then `AT+CRESET`. All three are stored in the modem and survive a power
   cycle. NetworkManager gives `usb0` metric 100, ahead of Wi-Fi's 600, so
   all traffic leaves over LTE when the modem is up.
7. **Power tuning**: `arm_freq`/`over_voltage` down, `maxcpus=1` in
   `cmdline.txt` for idle; read each step from the INA219 once the UPS
   Module 3S is fitted.

The button lights and the status LEDs are plain GPIO at 3.3 V (software PWM
through `gpiozero`) — nothing to enable in `config.txt`.
