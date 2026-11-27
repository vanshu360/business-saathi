"""Voice workflow: save the original transcript first, then Roman and English as separate,
individually retryable steps. A finished step is never sent to Sarvam again."""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..config import Settings
from ..database import utc_now
from ..errors import AppError, Conflict, InvalidRequest, NotFound
from ..languages import AUTO_DETECT, VALID_CODES
from ..repositories import transcriptions as repo
from .extraction import keyterms
from .speech.audio import EXTENSIONS, base_mime, delete_file, measure_seconds
from .speech.sarvam import MAX_SECONDS, SpeechError, estimate_cost_inr

MODES = {"original": "transcribe", "roman": "translit", "english": "translate"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
STALE_PROCESSING = timedelta(seconds=90)


class SpeechUnavailable(AppError):
    status_code = 503


def details(row) -> dict:
    seconds = row["duration_seconds"] or 0
    data = {k: row[k] for k in row.keys() if k not in ("audio_path", "audio_sha256", "shop_id")}
    data["audio_stored"] = row["audio_path"] is not None
    data["requests_planned"] = len(MODES)
    data["cost_so_far_inr"] = estimate_cost_inr(seconds, row["request_count"])
    data["cost_full_inr"] = estimate_cost_inr(seconds, len(MODES))
    return data


def cleanup_expired_audio(conn) -> int:
    rows = repo.expired_audio(conn, utc_now())
    for row in rows:
        delete_file(row["audio_path"])
        repo.clear_audio(conn, row["id"])
    conn.commit()
    return len(rows)


def create_from_upload(conn, settings: Settings, client, shop_id: int, audio: bytes, mime: str,
                       language: str, consent: bool, client_seconds: Optional[float]) -> dict:
    if client is None:
        raise SpeechUnavailable("Voice orders need a Sarvam API key. Use manual entry for now.")
    if not consent:
        raise InvalidRequest("Please accept the recording notice before sending audio to Sarvam.")
    if language not in VALID_CODES:
        raise InvalidRequest("Unknown language")
    if not audio:
        raise InvalidRequest("The recording is empty. Please record again.")
    if len(audio) > MAX_UPLOAD_BYTES:
        raise InvalidRequest("The recording is too large.")
    cleanup_expired_audio(conn)

    sha = hashlib.sha256(audio).hexdigest()
    reused = repo.find_reusable(conn, shop_id, sha, language)
    if reused:
        return {**details(reused), "reused": True}

    mime = base_mime(mime)
    path = settings.audio_dir / f"{sha[:32]}.{EXTENSIONS.get(mime, 'bin')}"
    path.write_bytes(audio)
    # Browsers' WebM files can under-report length; the larger value keeps cost and limit checks safe.
    seconds = max(filter(None, [measure_seconds(path), client_seconds]), default=None)
    if not seconds or seconds <= 0:
        delete_file(str(path))
        raise InvalidRequest("Could not read the recording. Please record again.")
    if seconds > MAX_SECONDS + 0.5:
        delete_file(str(path))
        raise InvalidRequest(f"Recordings can be at most {MAX_SECONDS} seconds.")

    delete_after = (datetime.now(timezone.utc) + timedelta(hours=settings.audio_retention_hours)
                    ).isoformat(timespec="seconds")
    tid = repo.insert(conn, shop_id, sha, str(path), mime or "application/octet-stream",
                      delete_after, round(seconds, 2), language)
    conn.commit()
    return {**process_output(conn, client, shop_id, tid, "original"), "reused": False}


def process_output(conn, client, shop_id: int, tid: int, output: str) -> dict:
    if output not in MODES:
        raise NotFound("Unknown output")
    row = repo.get(conn, shop_id, tid)
    if row is None:
        raise NotFound("Recording not found")
    status = row[f"{output}_status"]
    if status == "done":
        return details(row)
    if status == "processing" and datetime.fromisoformat(row["updated_at"]) > \
            datetime.now(timezone.utc) - STALE_PROCESSING:
        raise Conflict("This step is already running. Please wait.")
    if output != "original" and row["original_status"] != "done":
        raise InvalidRequest("The original transcript must be ready first.")
    if client is None:
        raise SpeechUnavailable("Voice orders need a Sarvam API key. Use manual entry for now.")
    if not row["audio_path"]:
        repo.set_status(conn, tid, output, "failed",
                        error="The recording was deleted (retention policy). Please record again.")
        conn.commit()
        return details(repo.get(conn, shop_id, tid))

    repo.set_status(conn, tid, output, "processing")
    conn.commit()
    language = row["language_detected"] if output != "original" and row["language_detected"] \
        else row["language_requested"]
    try:
        with open(row["audio_path"], "rb") as fh:
            audio = fh.read()
        result = client.transcribe(
            audio, f"order.{EXTENSIONS.get(row['audio_mime'], 'bin')}", row["audio_mime"],
            MODES[output], language or AUTO_DETECT,
            keyterms(conn, shop_id) if output != "english" else None)
    except SpeechError as exc:
        repo.set_status(conn, tid, output, "failed", error=exc.message, count_request=True)
    except OSError:
        repo.set_status(conn, tid, output, "failed",
                        error="The recording could not be read. Please record again.")
    else:
        if result.text:
            repo.set_status(conn, tid, output, "done", text=result.text, count_request=True)
        else:
            repo.set_status(conn, tid, output, "failed", count_request=True,
                            error="No speech was recognised. Please speak clearly and try again.")
        if output == "original":
            repo.set_language(conn, tid, result.language_code, result.language_probability)
    conn.commit()

    row = repo.get(conn, shop_id, tid)
    if all(row[f"{o}_status"] == "done" for o in MODES) and row["audio_path"]:
        delete_file(row["audio_path"])
        repo.clear_audio(conn, tid)
        conn.commit()
        row = repo.get(conn, shop_id, tid)
    return details(row)
