"""`dadboxctl` — the debug console as a CLI over a Unix socket. Build first."""
import sys

COMMANDS = ("state", "record", "play", "inbox", "outbox", "checkin", "modem", "led", "lock", "sim")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("usage: dadboxctl " + "|".join(COMMANDS), file=sys.stderr)
        return 2
    # TODO: connect to /run/dadbox.sock, send argv[1:], print the reply
    print("not implemented", file=sys.stderr)
    return 1
