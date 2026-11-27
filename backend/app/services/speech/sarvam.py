"""Sarvam Saaras v4 REST client (server side only; the API key never reaches the browser)."""
import json
from dataclasses import dataclass
from typing import Optional

import httpx

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
MODEL = "saaras:v4"
PRICE_PER_MINUTE_INR = 0.49  # pay-as-you-go, billed per second, before GST (docs checked 27-11-2026)
MAX_SECONDS = 30  # REST limit; longer audio needs the Batch API


@dataclass
class SpeechResult:
    text: str
    language_code: Optional[str]
    language_probability: Optional[float]


class SpeechError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


ERRORS_BY_STATUS = {
    400: "Sarvam could not read this recording. Please record again.",
    401: "Sarvam rejected the API key. Please check SARVAM_API_KEY.",
    403: "Sarvam rejected the API key. Please check SARVAM_API_KEY.",
    422: "Sarvam could not read this recording. Please record again.",
    429: "Sarvam limit reached (too many requests or no credit left). Wait a minute and retry.",
    500: "Sarvam had an internal error. Please retry.",
    503: "Sarvam is busy right now. Please retry in a moment.",
}


class SarvamClient:
    def __init__(self, api_key: str, timeout: float = 60.0,
                 transport: Optional[httpx.BaseTransport] = None):
        self._api_key = api_key
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def transcribe(self, audio: bytes, filename: str, mime: str, mode: str,
                   language_code: str, keyterms: Optional[list[str]] = None) -> SpeechResult:
        data = {"model": MODEL, "mode": mode, "language_code": language_code}
        if keyterms:
            data["keyterms"] = json.dumps(keyterms[:50], ensure_ascii=False)
        try:
            res = self._client.post(
                SARVAM_STT_URL, headers={"api-subscription-key": self._api_key},
                data=data, files={"file": (filename, audio, mime)})
        except httpx.TimeoutException:
            raise SpeechError("Sarvam took too long to answer. Please retry.")
        except httpx.HTTPError:
            raise SpeechError("Could not reach Sarvam. Check the internet connection and retry.")
        if res.status_code != 200:
            message = ERRORS_BY_STATUS.get(res.status_code, f"Sarvam returned error {res.status_code}. Please retry.")
            raise SpeechError(message)
        try:
            body = res.json()
        except ValueError:
            raise SpeechError("Sarvam sent an unreadable answer. Please retry.")
        return SpeechResult(text=(body.get("transcript") or "").strip(),
                            language_code=body.get("language_code"),
                            language_probability=body.get("language_probability"))


def estimate_cost_inr(seconds: float, requests: int) -> float:
    return round(seconds * requests / 60 * PRICE_PER_MINUTE_INR, 2)
