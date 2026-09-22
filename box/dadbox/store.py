"""Everything on `/data` — the only writable partition (ADR 0014, ADR 0010).

    /data/
      outbox/<id>.dbx      sealed container, fsynced before the got-it pulse; never evicted
      outbox/<id>.json     its metadata (the PUT body) + local state: queued | uploading
      inbox/<id>.dbx       a downloaded container, crc-checked; may be evicted
      inbox/<id>.json      { played: bool, reported: bool, broken: bool }
      capture/<id>.pcm     the live recording, raw s16le 16 kHz mono, fsynced every second
      capture/<id>.json    when it started (for created_at / time_ok); recovered at boot
      seq                  monotonic per-sender counter — the ordering key
      lock                 present ⇔ travel lock engaged (survives a reboot)
      settings.json        last settings from the server
      keys/<key_id>.key    32 bytes, hex — root 0600, never in this repo
      config.env           DADBOX_URL, DADBOX_TOKEN — root 0600

Every write is temp → fsync → rename, so a power pull leaves a file whole or
absent, never half. Directories are fsynced after renames so the rename
itself is durable.
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ids import is_ulid


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def write_json_atomic(path: Path, obj: Any) -> None:
    write_atomic(path, json.dumps(obj, separators=(",", ":"), sort_keys=True).encode())


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        for d in ("outbox", "inbox", "capture", "keys", "tmp"):
            (self.root / d).mkdir(parents=True, exist_ok=True)

    # --- identity and configuration ------------------------------------------------

    def config(self) -> Dict[str, str]:
        """DADBOX_URL / DADBOX_TOKEN from config.env, overridden by the environment."""
        out: Dict[str, str] = {}
        f = self.root / "config.env"
        if f.exists():
            for line in f.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip()
        for k in ("DADBOX_URL", "DADBOX_TOKEN"):
            if os.environ.get(k):
                out[k] = os.environ[k]
        return out

    def keys(self) -> Dict[int, bytes]:
        keys: Dict[int, bytes] = {}
        for f in (self.root / "keys").glob("*.key"):
            m = re.fullmatch(r"(\d+)", f.stem)
            if m:
                keys[int(m.group(1))] = bytes.fromhex(f.read_text().strip())
        return keys

    def put_key(self, key_id: int, key: bytes) -> None:
        path = self.root / "keys" / f"{key_id}.key"
        write_atomic(path, key.hex().encode())
        os.chmod(path, 0o600)

    def next_seq(self) -> int:
        f = self.root / "seq"
        n = int(f.read_text() or 0) + 1 if f.exists() else 1
        write_atomic(f, str(n).encode())
        return n

    def locked(self) -> bool:
        return (self.root / "lock").exists()

    def set_locked(self, locked: bool) -> None:
        f = self.root / "lock"
        if locked:
            write_atomic(f, b"locked\n")
        elif f.exists():
            f.unlink()
            _fsync_dir(self.root)

    def settings_json(self) -> Optional[Dict[str, Any]]:
        return read_json(self.root / "settings.json")

    def save_settings(self, settings: Dict[str, Any]) -> None:
        write_json_atomic(self.root / "settings.json", settings)

    # --- capture --------------------------------------------------------------------

    def capture_path(self, message_id: str) -> Path:
        return self.root / "capture" / f"{message_id}.pcm"

    def begin_capture(self, message_id: str, info: Dict[str, Any]) -> Path:
        write_json_atomic(self.root / "capture" / f"{message_id}.json", info)
        return self.capture_path(message_id)

    def capture_info(self, message_id: str) -> Dict[str, Any]:
        return read_json(self.root / "capture" / f"{message_id}.json", {}) or {}

    def pending_captures(self) -> List[str]:
        """Recordings a power cut interrupted: encoded and queued at boot as if
        stop had been pressed (ADR 0019)."""
        return sorted(p.stem for p in (self.root / "capture").glob("*.pcm") if is_ulid(p.stem))

    def remove_capture(self, message_id: str) -> None:
        for ext in (".pcm", ".json"):
            p = self.root / "capture" / f"{message_id}{ext}"
            if p.exists():
                p.unlink()
        _fsync_dir(self.root / "capture")

    # --- outbox ---------------------------------------------------------------------

    def enqueue(self, message_id: str, container: bytes, meta: Dict[str, Any]) -> None:
        """The got-it pulse may follow this call and not before."""
        write_atomic(self.root / "outbox" / f"{message_id}.dbx", container)
        write_json_atomic(self.root / "outbox" / f"{message_id}.json", dict(meta, state="queued"))

    def outbox_ids(self) -> List[str]:
        """Oldest first, by seq — the ordering key, not the clock."""
        items = []
        for p in (self.root / "outbox").glob("*.dbx"):
            meta = read_json(p.with_suffix(".json"), {}) or {}
            items.append((meta.get("seq", 0), p.stem))
        return [mid for _, mid in sorted(items)]

    def outbox_meta(self, message_id: str) -> Dict[str, Any]:
        return read_json(self.root / "outbox" / f"{message_id}.json", {}) or {}

    def outbox_container(self, message_id: str) -> bytes:
        return (self.root / "outbox" / f"{message_id}.dbx").read_bytes()

    def outbox_set_state(self, message_id: str, state: str) -> None:
        meta = self.outbox_meta(message_id)
        if meta.get("state") != state:
            write_json_atomic(self.root / "outbox" / f"{message_id}.json", dict(meta, state=state))

    def outbox_bytes(self) -> Dict[str, int]:
        return {p.stem: p.stat().st_size for p in (self.root / "outbox").glob("*.dbx")}

    def outbox_oldest_age_s(self, wall: float) -> int:
        times = [p.stat().st_mtime for p in (self.root / "outbox").glob("*.dbx")]
        return int(wall - min(times)) if times else 0

    def outbox_remove(self, message_id: str) -> None:
        """Only on the server's 2xx to `complete` (ADR 0010)."""
        for ext in (".dbx", ".json"):
            p = self.root / "outbox" / f"{message_id}{ext}"
            if p.exists():
                p.unlink()
        _fsync_dir(self.root / "outbox")

    # --- inbox ----------------------------------------------------------------------

    def inbox_put(self, message_id: str, container: bytes) -> None:
        write_atomic(self.root / "inbox" / f"{message_id}.dbx", container)
        write_json_atomic(self.root / "inbox" / f"{message_id}.json",
                          {"played": False, "reported": False, "broken": False})

    def inbox_has(self, message_id: str) -> bool:
        return (self.root / "inbox" / f"{message_id}.dbx").exists()

    def _inbox_flags(self, message_id: str) -> Dict[str, Any]:
        return read_json(self.root / "inbox" / f"{message_id}.json", {}) or {}

    def inbox_unheard(self) -> List[str]:
        """Oldest first: ULIDs sort by the sender's clock, which is what the parent meant."""
        out = []
        for p in (self.root / "inbox").glob("*.dbx"):
            f = self._inbox_flags(p.stem)
            if not f.get("played") and not f.get("broken"):
                out.append(p.stem)
        return sorted(out)

    def inbox_container(self, message_id: str) -> bytes:
        return (self.root / "inbox" / f"{message_id}.dbx").read_bytes()

    def inbox_mark(self, message_id: str, **flags: bool) -> None:
        f = self._inbox_flags(message_id)
        f.update(flags)
        write_json_atomic(self.root / "inbox" / f"{message_id}.json", f)

    def inbox_to_report(self) -> List[str]:
        """Played locally, not yet acknowledged by the server."""
        return sorted(p.stem for p in (self.root / "inbox").glob("*.dbx")
                      if self._inbox_flags(p.stem).get("played") and not self._inbox_flags(p.stem).get("reported"))

    def inbox_broken(self) -> List[str]:
        return sorted(p.stem for p in (self.root / "inbox").glob("*.json") if self._inbox_flags(p.stem).get("broken"))

    def inbox_remove(self, message_id: str) -> None:
        for ext in (".dbx", ".json"):
            p = self.root / "inbox" / f"{message_id}{ext}"
            if p.exists():
                p.unlink()
        _fsync_dir(self.root / "inbox")

    def inbox_count(self) -> int:
        return len(list((self.root / "inbox").glob("*.dbx")))

    # --- housekeeping ---------------------------------------------------------------

    def storage_pct(self) -> int:
        try:
            st = os.statvfs(str(self.root))
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            return int(round(100 * (1 - free / total))) if total else 0
        except OSError:
            return 0

    def tmp_dir(self) -> Path:
        return self.root / "tmp"

    def wipe_tmp(self) -> None:
        shutil.rmtree(self.root / "tmp", ignore_errors=True)
        (self.root / "tmp").mkdir(exist_ok=True)
