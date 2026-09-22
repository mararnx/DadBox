#!/usr/bin/env python3
"""Mint a bearer token for one identity. Prints the token ONCE and the SQL that
stores its SHA-256 — the server never sees or keeps the token itself
(PROTOCOL.md § Identities).

    python3 tools/mint_token.py box
    python3 tools/mint_token.py parent-a

Paste the SQL into the Supabase SQL editor (or `supabase db query`). Put the
token where it belongs — /data/keys on the box, the Keychain on the phone,
tools/fakebox/.env for the fake box — and nowhere else. Never in this repo.
Running it again for the same identity rotates the token: the old one stops
working the moment the SQL runs.
"""
import hashlib
import secrets
import sys

IDENTITIES = ("box", "parent-a", "parent-b")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in IDENTITIES:
        print(f"usage: mint_token.py {{{'|'.join(IDENTITIES)}}}", file=sys.stderr)
        return 2
    who = sys.argv[1]
    token = secrets.token_urlsafe(32)          # 256 bits
    digest = hashlib.sha256(token.encode()).hexdigest()
    print(f"token for {who} (shown once — store it now):\n\n  {token}\n")
    print("run this against the database:\n")
    print(f"  update identities set token_hash = '{digest}', rotated_at = now() where id = '{who}';\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
