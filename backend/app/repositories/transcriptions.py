import sqlite3
from typing import Optional

from ..database import utc_now

OUTPUTS = ("original", "roman", "english")


def get(conn: sqlite3.Connection, shop_id: int, tid: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM transcriptions WHERE id = ? AND shop_id = ?",
                        (tid, shop_id)).fetchone()


def find_reusable(conn, shop_id: int, sha256: str, language: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM transcriptions WHERE shop_id = ? AND audio_sha256 = ? "
        "AND language_requested = ? AND original_status = 'done' ORDER BY id DESC LIMIT 1",
        (shop_id, sha256, language)).fetchone()


def insert(conn, shop_id: int, sha256: str, path: str, mime: str, delete_after: str,
           seconds: float, language: str) -> int:
    now = utc_now()
    cur = conn.execute(
        "INSERT INTO transcriptions (shop_id, audio_sha256, audio_path, audio_mime, "
        "audio_delete_after, duration_seconds, api_type, language_requested, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'rest', ?, ?, ?)",
        (shop_id, sha256, path, mime, delete_after, seconds, language, now, now))
    return cur.lastrowid


def set_status(conn, tid: int, output: str, status: str, text: Optional[str] = None,
               error: Optional[str] = None, count_request: bool = False) -> None:
    assert output in OUTPUTS
    conn.execute(
        f"UPDATE transcriptions SET {output}_status = ?, {output}_text = COALESCE(?, {output}_text), "
        f"{output}_error = ?, request_count = request_count + ?, updated_at = ? WHERE id = ?",
        (status, text, error, 1 if count_request else 0, utc_now(), tid))


def set_language(conn, tid: int, code: Optional[str], probability: Optional[float]) -> None:
    conn.execute("UPDATE transcriptions SET language_detected = ?, language_probability = ? "
                 "WHERE id = ?", (code, probability, tid))


def clear_audio(conn, tid: int) -> None:
    conn.execute("UPDATE transcriptions SET audio_path = NULL WHERE id = ?", (tid,))


def expired_audio(conn, now: str) -> list[sqlite3.Row]:
    return conn.execute("SELECT id, audio_path FROM transcriptions WHERE audio_path IS NOT NULL "
                        "AND audio_delete_after <= ?", (now,)).fetchall()
