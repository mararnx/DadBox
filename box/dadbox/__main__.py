"""Service entry point. `python3 -m dadbox`. Everything below is a TODO with a name.

M0 order: ctl socket → ui (lid, button, ring, LEDs) → audio (capture to /data,
Opus on close, playback). Only then queue, link, power.
"""
import logging
import sys

log = logging.getLogger("dadbox")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    log.info("DadBox starting")
    # TODO: ctl.serve()        Unix socket for dadboxctl
    # TODO: ui.start()         lid interrupt → audio.start_capture(); button → audio.play_next()
    # TODO: audio              ALSA capture streamed to /data/capture.wav; ffmpeg → Opus on close
    # TODO: queue              /data/outbox, /data/inbox, fsync-then-rename, resume
    # TODO: link               VBUS switch, wait for the stick's interface, check-in loop
    # TODO: power              MAX17048 over I²C, LOW / ASLEEP behaviour
    return 0


if __name__ == "__main__":
    sys.exit(main())
