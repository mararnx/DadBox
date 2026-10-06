# Box setup — what Claude does over SSH after the first boot

1. **Packages**: `ffmpeg alsa-utils python3-venv python3-lgpio i2c-tools` and Tailscale
   (`curl -fsSL https://tailscale.com/install.sh | sh`). Its state must
   outlive the overlay: `/data/tailscale` (0700) bind-mounted on
   `/var/lib/tailscale` from fstab (`bind,x-systemd.requires-mounts-for=/data`),
   before `tailscale up --hostname=dadbox` — the auth link is the user's to
   open. `ssh dadbox` is then the Tailscale name, `ssh dadbox-lan` the home network.
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
   # modem power key (GPIO 4 = HAT P4): low from the first second, against its boot pull-up
   gpio=4=op,dl
   # Play all colours on from power-on, until dadbox-bootlight takes over (ADR 0024 §7)
   gpio=23,24,25=op,dh
   # in the field only; the bench needs Wi-Fi
   #dtoverlay=disable-wifi
   ```
   Plus, outside `config.txt`: `echo i2c-dev | sudo tee /etc/modules-load.d/i2c-dev.conf`
   (the `/dev/i2c-1` node), and the hardware watchdog armed by systemd:
   `/etc/systemd/system.conf.d/watchdog.conf` with `[Manager]` / `RuntimeWatchdogSec=15`.
3. **`/data`**: a third ext4 partition, `noatime`, mounted by label; root
   stays at 8 GB. Before the first boot, on the Mac, in the card's `bootfs`:
   delete the word `resize` from `cmdline.txt`, and add to `user-data`
   `growpart: {mode: "off"}` and `resize_rootfs: false` (the initramfs and
   cloud-init would each grow root over the whole card) — and set the user's
   `sudo:` to `"ALL=(ALL) NOPASSWD:ALL"`. After the first boot (root is
   2.3 GB), with `sfdisk` (the image has no `parted`):
   ```
   echo ",16777216" | sudo sfdisk -N 2 --no-reread /dev/mmcblk0       # root → 8 GiB
   echo "17842176,,83" | sudo sfdisk -a --no-reread /dev/mmcblk0      # p3: the rest
   sudo partx -u /dev/mmcblk0 && sudo partx -a /dev/mmcblk0; sudo resize2fs /dev/mmcblk0p2
   sudo mkfs.ext4 -L data /dev/mmcblk0p3
   echo "LABEL=data  /data  ext4  defaults,noatime  0  2" | sudo tee -a /etc/fstab
   ```
   Growing a mounted root is safe; shrinking one is not possible, which is
   why this happens before the first boot. `/opt/dadbox` → symlink to
   `/data/app`; the deploying user joins group `dadbox` (`/data` is 0750).
4. **Overlay** — last, after everything else is installed and the service runs:
   - `Storage=volatile`, `RuntimeMaxUse=16M` in `/etc/systemd/journald.conf.d/`;
     `Mechanism=zram` in `/etc/rpi/swap.conf.d/` (a swap *file* would land in RAM);
     `touch /etc/cloud/cloud-init.disabled` (it must never rewrite the network config).
   - `raspi-config nonint enable_overlayfs` and `enable_bootro`, then in
     `/boot/firmware/cmdline.txt` change `overlayroot=tmpfs` to
     **`overlayroot=tmpfs:recurse=0`**. Without it overlayroot puts every
     fstab mount under `/` in RAM too — `/data` included, and a recording would
     vanish at the next power cut. After the reboot `findmnt /data` must show
     `/dev/mmcblk0p3 ext4 rw`, not `overlay`.
   - Changing anything on root afterwards: `sudo raspi-config nonint disable_overlayfs`,
     reboot, change, enable, reboot. Only on the bench, never in the field.
5. **Service**, which runs as its own user, not root:
   ```
   sudo useradd --system --home /data --shell /usr/sbin/nologin \
        --groups gpio,audio,i2c,dialout dadbox
   sudo chown -R dadbox:dadbox /data
   echo 'dadbox ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff' | sudo tee /etc/sudoers.d/dadbox
   sudo chmod 0440 /etc/sudoers.d/dadbox && sudo visudo -c
   ```
   Code goes on with `box/deploy.sh` (rsync, then group `dadbox` and modes
   fixed on the Pi — macOS openrsync ignores `--chmod`).
   `python3 -m venv --system-site-packages /opt/dadbox/.venv` (so gpiozero
   finds apt's `lgpio`, which pip would have to compile), `pip install -e .[pi]`, the unit from
   `systemd/`, `systemctl enable --now dadbox`; also `systemctl enable
   dadbox-bootlight` (the power-on colours, ADR 0024 §7) and `dadbox-bootvoice`
   (the spoken "starting"; run `setup/make_voice.sh` from the Mac first, ADR 0024 §10). `dadboxctl` on `$PATH`.
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
   cycle. NetworkManager puts `usb0` on the `netplan-eth0` connection at
   metric 100, ahead of Wi-Fi's 600: everything leaves over LTE, as in the
   field (the SIM is unlimited). For a big `apt` install on the bench, Wi-Fi
   is several times faster — `sudo ip route del default dev usb0` until the
   next reboot.
7. **Power tuning**: `arm_freq`/`over_voltage` down, `maxcpus=1` in
   `cmdline.txt` for idle; read each step from the INA219 once the UPS
   Module 3S is fitted.

The button lights are plain GPIO at 3.3 V (software PWM
through `gpiozero`) — nothing to enable in `config.txt`.
