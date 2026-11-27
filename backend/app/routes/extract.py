import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from ..config import Settings
from ..database import DEFAULT_SHOP_ID as SHOP
from ..deps import db_conn, get_settings
from ..services.extraction import extract_order

router = APIRouter(prefix="/api", tags=["extraction"])


class ExtractRequest(BaseModel):
    original: str = Field(default="", max_length=5000)
    roman: Optional[str] = Field(default=None, max_length=5000)
    english: Optional[str] = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def _needs_text(self):
        if not (self.original.strip() or (self.roman or "").strip()):
            raise ValueError("Please provide the order text")
        return self


@router.post("/extract")
def extract(body: ExtractRequest, conn: sqlite3.Connection = Depends(db_conn),
            settings: Settings = Depends(get_settings)) -> dict:
    return extract_order(conn, SHOP, settings.timezone, body.original, body.roman,
                         body.english).to_dict()
