# Box setup — what Claude does over SSH after the first boot

1. **Packages**: `ffmpeg alsa-utils python3-venv i2c-tools` and Tailscale
   (`curl -fsSL https://tailscale.com/install.sh | sh`, then `tailscale up`
   — the auth link is the user's to open).
2. **`/boot/firmware/config.txt`**
   ```
   dtoverlay=googlevoicehat-soundcard   # ICS-43434 mic + MAX98357A amp on I2S (GPIO 18/19/20/21, sdmode GPIO 16)
   dtparam=audio=off                    # no onboard PWM audio
   dtparam=spi=on                       # WS2812 ring over SPI MOSI (GPIO 10)
   dtparam=i2c_arm=on                   # MAX17048 fuel gauge
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
6. **Stick**: plug in; it should appear as `eth0`/`usb0` (HiLink, `cdc_ether`)
   with DHCP from 192.168.8.1. No AT commands. Check `ip a`, `curl ifconfig.me`.
7. **Power tuning**: `arm_freq`/`over_voltage` down, `maxcpus=1` in
   `cmdline.txt` for idle; measure each step with the USB meter.
