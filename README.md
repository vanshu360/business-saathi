# Business Saathi

A voice-first order assistant for small Indian shops (kirana stores): **speak an order, check it, save it.**

Built for the Round 2 brief: *one core flow that works end to end, not a full product.*

> **Local demo only.** Single shop, no login. Do not put this on the public internet with real customer data.

## The core flow

1. Choose the language (22 Indian languages + English, or "Detect automatically").
2. Tick the recording notice (audio goes to Sarvam AI; it is deleted once processed).
3. Tap the microphone and speak the order (max 30 seconds).
4. Sarvam **Saaras v4** returns three texts, each shown separately:
   **Original** (saved first, the source of truth) · **Roman** · **English**.
5. The app fills an order form: customer, products, quantities, units, delivery.
   Anything unclear is marked **Check**, never guessed.
6. Correct anything, press **Confirm and save order**, confirm once more.
7. The saved order opens from SQLite. Reload the page: it is still there.

No Sarvam key? Use **Type an order**: type the sentence, the same reader fills the form.

## Run it (Docker Compose)

```bash
cp .env.example .env     # put your key after SARVAM_API_KEY= (optional)
docker compose up --build
```

Open http://localhost:8000. Data lives in the Docker volume `saathi_data` and survives restarts
(`docker compose down -v` deletes it).

The microphone works on `http://localhost`. On another device it needs HTTPS (browser rule).

## 3-minute demo script

| Time | Do | Say |
|---|---|---|
| 0:00 | Dashboard | "Shopkeepers take orders by phone and voice notes and write them down by hand." |
| 0:20 | New Voice Order → Hindi → tick notice | "Audio goes to Sarvam only with consent and is deleted after processing." |
| 0:35 | Record: *"Ramesh ji ko do kilo chawal, ek kilo chini aur do packet biscuit, kal shaam paanch baje"* | |
| 0:55 | Point at the three texts and the request/cost line | "Original first, then Roman and English. Each step can be retried alone; nothing is paid for twice." |
| 1:20 | Review form: fix a quantity, note the **Check** on "kal" | "The app never guesses. Unclear items are flagged." |
| 1:50 | Confirm and save → reload the page | "Saved in SQLite. It survives a reload and a restart." |
| 2:20 | Saved Orders → search "Ramesh" | |
| 2:35 | Type an Order (no key needed) | "Manual fallback when Sarvam is unavailable." |

## How it works

```
Browser (HTML/CSS/JS, MediaRecorder)
   │  audio + language + consent
   ▼
FastAPI ──► Sarvam Saaras v4 REST (3 requests: transcribe, translit, translate)
   │            key stays on the server (SARVAM_API_KEY)
   ├─► rule-based extractor (original transcript; Roman/English only cross-check)
   └─► SQLite (orders, items, history, transcripts)
```

- **Cost:** 3 requests per recording, about ₹0.49 for 20 seconds (₹0.49/min, before GST). Same audio is never re-sent.
- **Audio retention:** deleted as soon as all three texts are ready, or after `AUDIO_RETENTION_HOURS` (default 24).
- **Extraction** is pluggable (`backend/app/services/extraction/`); an AI extractor can be added later. The default has no API cost.

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Development

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest            # uses a fake Sarvam; no real API calls
```

`ffmpeg` should be installed (used to measure recording length; it is in the Docker image).

## Known limitations

- Recordings are limited to 30 seconds (Saaras REST limit); the Batch API is not used.
- Languages are marked "documented" until tested with a real recording.
- The rule-based reader knows a built-in grocery list and Hindi/English number and unit words; other languages rely on the Roman transcript cross-check and manual correction.
- No login, single shop: local/demo use only.
