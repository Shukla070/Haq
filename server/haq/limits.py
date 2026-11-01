"""Daily limits, so the public server cannot run up a model bill or fill its disk. Anyone can
make a device token, so a limit per device alone would stop nobody: there is also one per IP
address, set high because mobile networks share addresses, and one for the whole server.
Counts stay in memory and reset each day, so no IP address is ever written to disk."""

from __future__ import annotations

import os
import threading
from datetime import date

from . import config

MAX_RUNNING = 4  # agent runs at the same time
MAX_EVIDENCE = 15  # files on one case
MIN_FREE_DISK = 2 * 1024**3
_PER_DEVICE = {"case": 10, "upload": 30, "run": 8}
_PER_ADDRESS = {"case": 40, "upload": 150, "run": 30}
_WHOLE_SERVER = {"case": 100, "upload": 300, "run": 60}

_lock = threading.Lock()
_day: date | None = None
_counts: dict = {}


class LimitReached(Exception):
    pass


def _server_limit(kind: str) -> int:
    return int(os.environ.get(f"HAQ_MAX_{kind.upper()}S_PER_DAY") or _WHOLE_SERVER[kind])


def spend(kind: str, device: str, address: str) -> None:
    """Count one case, upload or agent run, or raise LimitReached and count nothing."""
    global _day
    keys = [
        (("device", kind, device), _PER_DEVICE[kind]),
        (("address", kind, address), _PER_ADDRESS[kind]),
        (("server", kind), _server_limit(kind)),
    ]
    with _lock:
        if _day != config.today():
            _day = config.today()
            _counts.clear()
        if any(_counts.get(key, 0) >= limit for key, limit in keys):
            raise LimitReached(kind)
        for key, _limit in keys:
            _counts[key] = _counts.get(key, 0) + 1


def reset() -> None:
    with _lock:
        _counts.clear()
