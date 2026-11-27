"""Health and configuration status. Never returns the API key itself."""
import sqlite3

from fastapi import APIRouter, Depends

from ..config import Settings
from ..deps import db_conn, get_settings

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health(conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    conn.execute("SELECT 1").fetchone()
    return {"status": "ok", "database": "ok"}


@router.get("/system/status")
def system_status(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "app": "Business Saathi",
        "mode": "single-shop, local/demo only",
        "sarvam_configured": settings.sarvam_configured,
        "sarvam_message": (
            "Sarvam AI is configured. Voice orders are available."
            if settings.sarvam_configured
            else "Sarvam AI is not configured (SARVAM_API_KEY is empty). "
            "Voice orders are unavailable; manual order entry works normally."
        ),
        "audio_retention_hours": settings.audio_retention_hours,
        "timezone": settings.timezone,
    }
