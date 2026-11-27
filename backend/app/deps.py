"""Shared FastAPI dependencies."""
import sqlite3
from typing import Iterator

from fastapi import Request

from .config import Settings
from .database import get_db


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def db_conn(request: Request) -> Iterator[sqlite3.Connection]:
    with get_db(request.app.state.settings) as conn:
        yield conn
