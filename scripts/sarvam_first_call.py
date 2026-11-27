"""One real Saaras v4 call: python scripts/sarvam_first_call.py <audio file> [transcribe|translit|translate]

Reads SARVAM_API_KEY from the environment or the project's .env file; the key is never printed.
"""
import os
import sys
from pathlib import Path

from sarvamai import SarvamAI

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def api_key() -> str:
    if os.getenv("SARVAM_API_KEY"):
        return os.environ["SARVAM_API_KEY"]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "SARVAM_API_KEY" and value.strip():
                return value.strip()
    sys.exit("SARVAM_API_KEY is not set. Add it to .env (see .env.example).")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    audio, mode = Path(sys.argv[1]), (sys.argv[2] if len(sys.argv) > 2 else "transcribe")
    client = SarvamAI(api_subscription_key=api_key())
    with audio.open("rb") as f:
        res = client.speech_to_text.transcribe(file=f, model="saaras:v4", mode=mode, language_code="unknown")
    print(f"mode: {mode}\nlanguage: {res.language_code} ({res.language_probability})\ntranscript: {res.transcript}")


if __name__ == "__main__":
    main()
