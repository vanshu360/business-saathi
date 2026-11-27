"""Audio helpers: measure length with ffmpeg and store/delete temporary recordings."""
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

EXTENSIONS = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/wav": "wav", "audio/x-wav": "wav",
              "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/aac": "aac"}
TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")


def measure_seconds(path: Path) -> Optional[float]:
    """Decode the file to find its real length (browser WebM files often have no duration header)."""
    if not shutil.which("ffmpeg"):
        return None
    try:
        proc = subprocess.run(["ffmpeg", "-hide_banner", "-protocol_whitelist", "file", "-i",
                               str(path), "-f", "null", "-"],
                              capture_output=True, text=True, timeout=20)
    except (subprocess.SubprocessError, OSError):
        return None
    times = TIME_RE.findall(proc.stderr)
    if proc.returncode != 0 or not times:
        return None
    h, m, s = times[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def base_mime(mime: str) -> str:
    return (mime or "").split(";")[0].strip().lower()


def delete_file(path: Optional[str]) -> None:
    if path:
        Path(path).unlink(missing_ok=True)
