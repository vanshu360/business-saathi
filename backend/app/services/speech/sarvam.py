"""Sarvam Saaras v4 client using the official sarvamai SDK (server side only; the key never reaches the browser)."""
from dataclasses import dataclass
from typing import Optional

import httpx
from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError

MODEL = "saaras:v4"
PRICE_PER_MINUTE_INR = 0.49  # pay-as-you-go, billed per second, before GST (docs checked 27-11-2026)
MAX_SECONDS = 30  # REST limit; longer audio needs the Batch API
NO_SDK_RETRIES = {"max_retries": 0}  # each attempt is billed, so retries stay a visible shopkeeper action


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
        self._sdk = SarvamAI(api_subscription_key=api_key,
                             httpx_client=httpx.Client(timeout=timeout, transport=transport))

    def transcribe(self, audio: bytes, filename: str, mime: str, mode: str,
                   language_code: str, keyterms: Optional[list[str]] = None) -> SpeechResult:
        extra = {"keyterms": keyterms[:50]} if keyterms else {}
        try:
            res = self._sdk.speech_to_text.transcribe(
                file=(filename, audio, mime), model=MODEL, mode=mode, language_code=language_code,
                request_options=NO_SDK_RETRIES, **extra)
        except ApiError as err:
            status = err.status_code or 0
            if 200 <= status < 300:
                raise SpeechError("Sarvam sent an unreadable answer. Please retry.")
            raise SpeechError(ERRORS_BY_STATUS.get(status, f"Sarvam returned error {status}. Please retry."))
        except httpx.TimeoutException:
            raise SpeechError("Sarvam took too long to answer. Please retry.")
        except httpx.HTTPError:
            raise SpeechError("Could not reach Sarvam. Check the internet connection and retry.")
        except ValueError:
            raise SpeechError("Sarvam sent an unreadable answer. Please retry.")
        return SpeechResult(text=(res.transcript or "").strip(), language_code=res.language_code,
                            language_probability=res.language_probability)


def estimate_cost_inr(seconds: float, requests: int) -> float:
    return round(seconds * requests / 60 * PRICE_PER_MINUTE_INR, 2)
