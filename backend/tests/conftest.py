import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_settings(tmp_path, api_key: str = "") -> Settings:
    return Settings(
        sarvam_api_key=api_key,
        data_dir=tmp_path / "data",
        audio_retention_hours=24,
        timezone="Asia/Kolkata",
    )


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c
