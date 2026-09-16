"""
BAS-APG — Orbital-Grade Logger (§5.2)

Two-tier logging:
  1. RotatingFileHandler → disk (5MB cap, 3 backups) for post-mission audit
  2. In-memory deque(maxlen=6) → WebSocket payload (FIX 18: zero disk I/O at 30 Hz)   
"""

import logging
from collections import deque
from logging.handlers import RotatingFileHandler

class _InMemoryHandler(logging.Handler):
    """Captures the most recent log lines in a thread-safe deque.

    The WebSocket telemetry payload reads from this deque at 30 Hz
    instead of hitting the filesystem (FIX 18).
    """

    def __init__(self, maxlen: int = 6):
        super().__init__()
        self._buffer: deque[str] = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._buffer.append(msg)
            from app.core.state import MissionState
            logs = list(MissionState.recent_logs)
            logs.append(msg)
            MissionState.recent_logs = logs[-6:]
        except Exception:
            self.handleError(record)

    def get_recent_logs(self, limit: int = 6) -> list[str]:
        """Return the most recent log lines as a plain list (JSON-safe).

        FIX 39: collections.deque is not JSON-serializable — always
        return list().
        """
        return list(self._buffer)[-limit:]


blackbox_logger = logging.getLogger("BAS_APG_BlackBox")
blackbox_logger.setLevel(logging.INFO)


_file_handler = RotatingFileHandler(
    "bas_apg_flight.log", 
    maxBytes=5*1024*1024, 
    backupCount=3
)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
)
blackbox_logger.addHandler(_file_handler)


_mem_handler = _InMemoryHandler(maxlen=6)
_mem_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
)
blackbox_logger.addHandler(_mem_handler)

def get_recent_logs(limit: int = 6) -> list[str]:
    """Module-level convenience accessor for the in-memory log buffer."""
    return _mem_handler.get_recent_logs(limit)
