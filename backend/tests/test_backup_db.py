import sqlite3

from scripts.backup_db import backup_db, _db_path


def test_backup_creates_valid_readable_copy_and_prunes():
    src = _db_path()
    if not src.exists():
        # Real DB may be absent in a clean checkout; create a minimal one.
        with sqlite3.connect(src) as c:
            c.execute("CREATE TABLE IF NOT EXISTS t(x)")
            c.execute("INSERT INTO t VALUES (1)")

    # Write 3 backups with retain=2 -> only the 2 newest survive.
    paths = [backup_db(retain=2, stamp=f"20260101T00000{i}Z") for i in range(3)]
    assert paths[-1].exists()
    assert not paths[0].exists()  # oldest pruned

    # The backup is a valid, queryable SQLite file.
    with sqlite3.connect(paths[-1]) as c:
        c.execute("SELECT name FROM sqlite_master").fetchall()
