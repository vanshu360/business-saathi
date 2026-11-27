import sqlite3
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from ..config import Settings
from ..database import DEFAULT_SHOP_ID as SHOP
from ..deps import db_conn, get_settings
from ..errors import NotFound
from ..repositories import transcriptions as repo
from ..services import transcription as service

router = APIRouter(prefix="/api/transcriptions", tags=["voice"])


def speech_client(request: Request):
    return request.app.state.speech_client


@router.post("", status_code=201)
def upload(file: UploadFile = File(...), language: str = Form("unknown"),
                 consent: bool = Form(False), duration_seconds: Optional[float] = Form(None),
                 conn: sqlite3.Connection = Depends(db_conn),
                 settings: Settings = Depends(get_settings), client=Depends(speech_client)) -> dict:
    audio = file.file.read(service.MAX_UPLOAD_BYTES + 1)
    return service.create_from_upload(conn, settings, client, SHOP, audio, file.content_type or "",
                                      language, consent, duration_seconds)


@router.get("/{tid}")
def get_one(tid: int, conn: sqlite3.Connection = Depends(db_conn)) -> dict:
    service.cleanup_expired_audio(conn)
    row = repo.get(conn, SHOP, tid)
    if row is None:
        raise NotFound("Recording not found")
    return service.details(row)


@router.post("/{tid}/outputs/{output}")
def process(tid: int, output: Literal["original", "roman", "english"],
            conn: sqlite3.Connection = Depends(db_conn), client=Depends(speech_client)) -> dict:
    return service.process_output(conn, client, SHOP, tid, output)
