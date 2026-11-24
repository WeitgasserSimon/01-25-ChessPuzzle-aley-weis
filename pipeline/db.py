import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
DEFAULT_DB = Path(__file__).resolve().parent.parent / "db" / "positions.db"
SCHEMA_VERSION = 1


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def delete_db(db_path):
    for suffix in ("", "-wal", "-shm"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)


def init_db(db_path, force=False):
    """Legt die Datenbank aus schema.sql an. Mit force wird eine vorhandene gelöscht."""
    db_path = Path(db_path)
    if db_path.exists():
        if not force:
            raise FileExistsError(f"Datenbank existiert schon: {db_path} (mit --force neu anlegen)")
        delete_db(db_path)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = connect(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    except sqlite3.Error:
        conn.close()
        delete_db(db_path)
        raise

    version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()
    if version != SCHEMA_VERSION:
        raise RuntimeError(f"schema.sql hat Version {version}, erwartet {SCHEMA_VERSION}")
