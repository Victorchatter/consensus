"""Quick database viewer -- prints all tables and their row counts."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent.parent / "database" / "echotrader.db"
print(f"Database: {db_path}")
print(f"Exists:   {db_path.exists()}")
print("=" * 50)

if not db_path.exists():
    print("Database file not found.")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

for (table_name,) in tables:
    cursor.execute(f"SELECT COUNT(*) FROM \"{table_name}\";")
    count = cursor.fetchone()[0]
    print(f"\nTable: {table_name} ({count} rows)")
    print("-" * 40)

    # Show first 10 rows
    cursor.execute(f"SELECT * FROM \"{table_name}\" LIMIT 10;")
    rows = cursor.fetchall()
    if rows:
        cursor.execute(f"PRAGMA table_info(\"{table_name}\");")
        cols = [c[1] for c in cursor.fetchall()]
        print(" | ".join(cols))
        print("-" * 40)
        for row in rows:
            print(" | ".join(str(c)[:30] for c in row))
    else:
        print("(empty)")

conn.close()
print("\nDone.")
