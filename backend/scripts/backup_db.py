"""Online backup of the SQLite database to database/backups/, timestamped.

Uses sqlite3's backup API, which is safe to run while the bot/UI hold the DB
open (no corruption from copying a live file). Keeps the most recent N backups.

Run manually:        ./venv/Scripts/python.exe -m scripts.backup_db
Schedule (Windows):  schtasks /create /tn EchoTraderBackup /sc DAILY /st 02:00 \
    /tr "C:\\Users\\Victor\\echotrader\\backend\\venv\\Scripts\\python.exe -m scripts.backup_db"
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import settings  # noqa: E402


def _db_path() -> Path:
    url = settings.database_url
    return Path(url.replace("sqlite:///", "")) if url.startswith("sqlite:///") else Path(url)


def backup_db(retain: int = 7, stamp: str | None = None) -> Path:
    """Write a consistent backup copy; prune to the newest `retain`. Returns the
    backup path. `stamp` is injectable for testing (avoids time in unit tests)."""
    src = _db_path()
    if not src.exists():
        raise FileNotFoundError(f"database not found: {src}")
    backups = src.parent / "backups"
    backups.mkdir(exist_ok=True)
    if stamp is None:
        # Imported lazily so module import stays side-effect-free for tests.
        from datetime import datetime, timezone

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst = backups / f"{src.stem}-{stamp}.db"

    # Explicit close (not just `with`, which commits but leaves the handle open
    # on CPython — a held handle blocks pruning/unlink on Windows).
    s = sqlite3.connect(src)
    d = sqlite3.connect(dst)
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()

    # Prune oldest, keep newest `retain` by filename (timestamps sort lexically).
    existing = sorted(backups.glob(f"{src.stem}-*.db"))
    for old in existing[:-retain] if retain > 0 else []:
        old.unlink(missing_ok=True)
    return dst


def main() -> int:
    dst = backup_db()
    print(f"[backup] wrote {dst}  ({dst.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
