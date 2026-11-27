"""Creates the FastAPI application and serves the frontend."""
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, load_settings
from .database import init_db
from .errors import AppError
from .routes import customers, orders, products, system

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()
    init_db(settings)

    app = FastAPI(title="Business Saathi", version="0.1.0")
    app.state.settings = settings
    for module in (system, products, customers, orders):
        app.include_router(module.router)

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app


app = create_app()
