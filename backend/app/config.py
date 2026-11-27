"""Reads settings from environment variables (see .env.example)."""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    sarvam_api_key: str
    data_dir: Path
    audio_retention_hours: int
    timezone: str

    @property
    def database_path(self) -> Path:
        return self.data_dir / "business_saathi.db"

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def sarvam_configured(self) -> bool:
        return bool(self.sarvam_api_key)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def load_settings() -> Settings:
    default_data = Path(__file__).resolve().parents[2] / "data"
    return Settings(
        sarvam_api_key=os.getenv("SARVAM_API_KEY", "").strip(),
        data_dir=Path(os.getenv("DATA_DIR", "").strip() or default_data),
        audio_retention_hours=_int_env("AUDIO_RETENTION_HOURS", 24),
        timezone=os.getenv("APP_TIMEZONE", "").strip() or "Asia/Kolkata",
    )
