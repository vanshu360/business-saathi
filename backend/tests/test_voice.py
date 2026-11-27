"""Voice workflow with a fake Sarvam client: no real API calls or costs in tests."""
import io
import json
import subprocess

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.speech.sarvam import SarvamClient, SpeechError, SpeechResult
from tests.conftest import make_settings

TEXTS = {"transcribe": "रमेश जी को दो किलो चावल", "translit": "Ramesh ji ko do kilo chawal",
         "translate": "Two kilos of rice for Ramesh"}


class FakeSarvam:
    def __init__(self):
        self.calls, self.fail_modes = [], set()

    def transcribe(self, audio, filename, mime, mode, language_code, keyterms=None):
        self.calls.append((mode, language_code, bool(keyterms)))
        if mode in self.fail_modes:
            raise SpeechError("Sarvam is busy right now. Please retry in a moment.")
        return SpeechResult(TEXTS[mode], "hi-IN", 0.97)


@pytest.fixture
def audio_bytes(tmp_path):
    path = tmp_path / "clip.webm"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=2",
                    "-c:a", "libopus", str(path)], check=True)
    return path.read_bytes()


@pytest.fixture
def voice(tmp_path):
    settings = make_settings(tmp_path, api_key="test-key")
    app = create_app(settings)
    fake = FakeSarvam()
    app.state.speech_client = fake
    with TestClient(app) as c:
        yield c, fake, settings


def upload(c, data, consent="true", language="unknown"):
    return c.post("/api/transcriptions", data={"language": language, "consent": consent},
                  files={"file": ("order.webm", io.BytesIO(data), "audio/webm;codecs=opus")})


def test_original_saved_first_then_each_output_separately(voice, audio_bytes):
    c, fake, settings = voice
    res = upload(c, audio_bytes)
    assert res.status_code == 201
    t = res.json()
    assert t["original_status"] == "done" and t["original_text"] == TEXTS["transcribe"]
    assert (t["roman_status"], t["english_status"]) == ("pending", "pending")
    assert t["language_detected"] == "hi-IN" and t["request_count"] == 1
    assert 1.9 < t["duration_seconds"] < 2.1 and t["audio_stored"]
    assert "audio_path" not in t and fake.calls == [("transcribe", "unknown", True)]

    t = c.post(f"/api/transcriptions/{t['id']}/outputs/roman").json()
    assert t["roman_text"] == TEXTS["translit"]
    t = c.post(f"/api/transcriptions/{t['id']}/outputs/english").json()
    assert t["english_text"] == TEXTS["translate"] and t["request_count"] == 3
    # detected language is reused, and English is not biased with Hindi keyterms
    assert fake.calls[1:] == [("translit", "hi-IN", True), ("translate", "hi-IN", False)]
    # all three outputs done -> temporary audio deleted at once
    assert not t["audio_stored"] and list(settings.audio_dir.iterdir()) == []
    assert t["cost_so_far_inr"] == t["cost_full_inr"]


def test_finished_steps_and_same_audio_are_not_paid_for_twice(voice, audio_bytes):
    c, fake, _ = voice
    t = upload(c, audio_bytes).json()
    c.post(f"/api/transcriptions/{t['id']}/outputs/original")
    again = upload(c, audio_bytes).json()
    assert again["reused"] and again["id"] == t["id"]
    assert len(fake.calls) == 1


def test_failed_translation_can_be_retried_alone(voice, audio_bytes):
    c, fake, _ = voice
    fake.fail_modes = {"translate"}
    t = upload(c, audio_bytes).json()
    c.post(f"/api/transcriptions/{t['id']}/outputs/roman")
    t = c.post(f"/api/transcriptions/{t['id']}/outputs/english").json()
    assert t["english_status"] == "failed" and "busy" in t["english_error"]
    assert t["original_text"] == TEXTS["transcribe"] and t["audio_stored"]
    fake.fail_modes = set()
    t = c.post(f"/api/transcriptions/{t['id']}/outputs/english").json()
    assert t["english_status"] == "done" and t["english_error"] is None
    assert [m for m, _, _ in fake.calls] == ["transcribe", "translit", "translate", "translate"]


def test_failed_original_keeps_record_for_retry(voice, audio_bytes):
    c, fake, _ = voice
    fake.fail_modes = {"transcribe"}
    t = upload(c, audio_bytes).json()
    assert t["original_status"] == "failed"
    assert c.post(f"/api/transcriptions/{t['id']}/outputs/roman").status_code == 400
    fake.fail_modes = set()
    assert c.post(f"/api/transcriptions/{t['id']}/outputs/original").json()["original_status"] == "done"


def test_consent_required(voice, audio_bytes):
    c, fake, _ = voice
    res = upload(c, audio_bytes, consent="false")
    assert res.status_code == 400 and "recording notice" in res.json()["detail"]
    assert fake.calls == []


def test_recordings_longer_than_30_seconds_rejected(voice, tmp_path):
    c, fake, settings = voice
    path = tmp_path / "long.webm"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=31",
                    "-c:a", "libopus", "-b:a", "8k", str(path)], check=True)
    res = upload(c, path.read_bytes())
    assert res.status_code == 400 and "30 seconds" in res.json()["detail"]
    assert fake.calls == [] and list(settings.audio_dir.iterdir()) == []


def test_unknown_language_and_empty_audio_rejected(voice, audio_bytes):
    c, _, _ = voice
    assert upload(c, audio_bytes, language="xx-IN").status_code == 400
    assert upload(c, b"").status_code == 400


def test_missing_key_gives_clear_message_and_manual_entry_still_works(client, audio_bytes):
    res = upload(client, audio_bytes)
    assert res.status_code == 503 and "manual entry" in res.json()["detail"]
    order = client.post("/api/orders", json={
        "customer_name": "Walk-in", "idempotency_key": "manual-0001",
        "items": [{"product_name": "Rice", "quantity": 1, "unit": "kg"}]})
    assert order.status_code == 201


def test_expired_audio_is_deleted_and_retry_explains(voice, audio_bytes):
    c, fake, settings = voice
    fake.fail_modes = {"translit"}
    t = upload(c, audio_bytes).json()
    from app.database import get_db
    with get_db(settings) as conn:
        conn.execute("UPDATE transcriptions SET audio_delete_after = '2000-01-01T00:00:00+00:00'")
        from app.services.transcription import cleanup_expired_audio
        assert cleanup_expired_audio(conn) == 1
    assert list(settings.audio_dir.iterdir()) == []
    t = c.post(f"/api/transcriptions/{t['id']}/outputs/roman").json()
    assert t["roman_status"] == "failed" and "retention" in t["roman_error"]
    assert t["original_text"] == TEXTS["transcribe"]


def test_voice_order_links_transcription(voice, audio_bytes):
    c, _, _ = voice
    t = upload(c, audio_bytes).json()
    order = c.post("/api/orders", json={
        "customer_name": "Ramesh", "source": "voice", "transcription_id": t["id"],
        "idempotency_key": "voice-0001",
        "items": [{"product_name": "Rice", "quantity": 2, "unit": "kg"}]}).json()
    assert order["transcription_id"] == t["id"]


# ---- the real HTTP client, against a mocked Sarvam server ------------------------------
def mocked_client(handler):
    return SarvamClient("secret-key", transport=httpx.MockTransport(handler))


def test_sarvam_client_sends_documented_fields():
    seen = {}

    def handler(request: httpx.Request):
        seen["key"] = request.headers["api-subscription-key"]
        seen["body"] = request.content.decode("utf-8", "ignore")
        return httpx.Response(200, json={"request_id": "r1", "transcript": " namaste ",
                                         "language_code": "hi-IN", "language_probability": 0.9})

    result = mocked_client(handler).transcribe(b"abc", "a.webm", "audio/webm", "translit",
                                               "unknown", ["चावल", "Rice"])
    assert result.text == "namaste" and result.language_code == "hi-IN"
    assert seen["key"] == "secret-key"
    for field in ('name="model"', "saaras:v4", 'name="mode"', "translit", 'name="language_code"',
                  json.dumps(["चावल", "Rice"], ensure_ascii=False), 'name="file"'):
        assert field in seen["body"]


@pytest.mark.parametrize("status,words", [(403, "API key"), (429, "limit"), (503, "busy"),
                                          (500, "internal"), (418, "error 418")])
def test_sarvam_errors_become_friendly_messages(status, words):
    client = mocked_client(lambda r: httpx.Response(status, json={"error": {"message": "x"}}))
    with pytest.raises(SpeechError) as err:
        client.transcribe(b"a", "a.webm", "audio/webm", "transcribe", "hi-IN")
    assert words in err.value.message and "secret" not in err.value.message


def test_network_failure_does_not_crash():
    def handler(request):
        raise httpx.ConnectError("offline")
    with pytest.raises(SpeechError) as err:
        mocked_client(handler).transcribe(b"a", "a.webm", "audio/webm", "transcribe", "hi-IN")
    assert "internet" in err.value.message
