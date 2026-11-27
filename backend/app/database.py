"""SQLite connection helpers and table creation."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import Settings

SCHEMA_FILE = Path(__file__).with_name("schema.sql")
DEFAULT_SHOP_ID = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    with connect(settings.database_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT OR IGNORE INTO shops (id, name, created_at) VALUES (?, ?, ?)",
            (DEFAULT_SHOP_ID, "My Shop", utc_now()),
        )
        from .catalogue_seed import seed_catalogue
        seed_catalogue(conn, DEFAULT_SHOP_ID)


@contextmanager
def get_db(settings: Settings) -> Iterator[sqlite3.Connection]:
    """Opens a connection, commits on success, rolls back on error."""
    conn = connect(settings.database_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
