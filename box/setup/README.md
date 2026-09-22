# Box setup — what Claude does over SSH after the first boot

1. **Packages**: `ffmpeg alsa-utils python3-venv python3-systemd i2c-tools` and Tailscale
   (`curl -fsSL https://tailscale.com/install.sh | sh`, then `tailscale up`
   — the auth link is the user's to open).
2. **`/boot/firmware/config.txt`**
   ```
   dtoverlay=googlevoicehat-soundcard   # DFRobot I2S mic + MAX98357A amp on I2S (GPIO 18/19/20/21, sdmode GPIO 16) — do not also load max98357a
   dtparam=audio=off                    # no onboard PWM audio
   dtparam=i2c_arm=on                   # INA219 on the UPS Module 3S
   dtparam=watchdog=on
   dtoverlay=disable-bt
   dtoverlay=disable-wifi               # in the field; comment out on the bench
   hdmi_blanking=2
   ```
3. **`/data`**: a second ext4 partition on the SD card, `noatime`, mounted
   by label. `/opt/dadbox` → symlink into `/data/app`.
4. **Overlay**: `raspi-config nonint enable_overlayfs` — after everything else
   is installed. Disable it only on the bench, never in the field.
5. **Service**: `.venv` under `/opt/dadbox`, `pip install -e .[pi]`,
   `systemctl enable --now dadbox`. `dadboxctl` on `$PATH`.
   Before the first start: `/data/config.env` with `DADBOX_URL` and
   `DADBOX_TOKEN` (root, 0600) and the family key in `/data/keys/1.key`
   (64 hex characters, root, 0600) — see `store.py` for the layout. Without
   them the service runs, records and queues, and cannot send.
6. **Modem** (SIM7670G HAT on the Zero's OTG port): confirm it enumerates as
   a USB Ethernet interface (`ip a`) and find its AT port (`/dev/ttyUSB*`;
   `AT+CSQ`, `AT+CPSI?`). If it does not come up as Ethernet, the mode is set
   once over AT — the exact command is to be confirmed from the Waveshare wiki
   with the part in hand. Then `curl ifconfig.me`, and check that the mode
   survives a reboot and a power-key cycle.
7. **Power tuning**: `arm_freq`/`over_voltage` down, `maxcpus=1` in
   `cmdline.txt` for idle; read each step from the INA219 once the UPS
   Module 3S is fitted.

The button lights and the status LEDs are plain GPIO at 3.3 V (software PWM
through `gpiozero`) — nothing to enable in `config.txt`.
