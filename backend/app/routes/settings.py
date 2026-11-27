import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from ..config import Settings
from ..database import DEFAULT_SHOP_ID as SHOP
from ..deps import db_conn, get_settings
from ..languages import VALID_CODES, language_list
from ..repositories import settings as repo

router = APIRouter(prefix="/api", tags=["settings"])


class ShopSettings(BaseModel):
    shop_name: str = Field(min_length=1, max_length=80)
    default_language: str = "unknown"
    time_format: Literal["12h", "24h"] = "12h"

    @field_validator("default_language")
    @classmethod
    def _valid_language(cls, v: str) -> str:
        if v not in VALID_CODES:
            raise ValueError("Unknown language code")
        return v


def _response(conn, settings: Settings) -> dict:
    return {
        **repo.get_all(conn, SHOP),
        "audio_retention_hours": settings.audio_retention_hours,
        "timezone": settings.timezone,
        "sarvam_configured": settings.sarvam_configured,
        "database_path": str(settings.database_path),
    }


@router.get("/settings")
def get_shop_settings(conn: sqlite3.Connection = Depends(db_conn),
                      settings: Settings = Depends(get_settings)) -> dict:
    return _response(conn, settings)


@router.put("/settings")
def update_shop_settings(data: ShopSettings, conn: sqlite3.Connection = Depends(db_conn),
                         settings: Settings = Depends(get_settings)) -> dict:
    repo.save(conn, SHOP, data.model_dump())
    return _response(conn, settings)


@router.get("/languages")
def languages() -> list[dict]:
    return language_list()
