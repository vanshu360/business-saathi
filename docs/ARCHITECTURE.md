# Business Saathi — Phase 1: Architecture and Plan

Status: **approved 27-11-2026 with refinements (section 11).** Built milestone by milestone.

Sarvam facts below were checked against docs.sarvam.ai on 27-11-2026. Pages used:
- Speech-to-Text overview: https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/overview
- Saaras model page: https://docs.sarvam.ai/api/api-guides-tutorials/models/saaras
- REST reference: https://docs.sarvam.ai/api-reference/speech-to-text/transcribe
- Batch API: https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/batch-api
- Pricing and rate limits: https://docs.sarvam.ai/api/getting-started/pricing

---

## 1. System architecture

In simple words: the shopkeeper's browser shows the screens. A small Python server (FastAPI) receives requests from the browser, saves data in one SQLite file, and is the **only** part that talks to Sarvam. The API key never reaches the browser.

```
 Phone / laptop browser  (HTML + CSS + plain JavaScript)
        |
        |  REST calls (JSON, and audio upload)
        v
 FastAPI backend (Python) ---------------------------+
   |  routes/      -> receive requests, validate input|
   |  services/    -> business rules                  |
   |     speech/   -> speech provider (Sarvam today)  |---> Sarvam Saaras v4
   |     extraction/ -> turns text into an order      |     (only if SARVAM_API_KEY set)
   |  repositories/ -> all database reads/writes      |
   v                                                  |
 SQLite file  (/data/business_saathi.db, Docker volume)
 Temporary audio files (/data/audio, auto-deleted)
```

Why these choices:
- **Plain HTML/CSS/JS** (no React): nothing to compile, easy for a beginner to read. FastAPI serves these files itself, so there is only one container.
- **Layers** (routes → services → repositories): each file has one job, so a bug is easy to locate. Speech, extraction and database code never mix.
- **Speech "provider" interface**: Sarvam is one implementation. Another provider can be added later without touching order code.
- **Works with no key**: if `SARVAM_API_KEY` is missing, voice features show a clear "not configured" message; manual entry, orders, customers and products all still work.

## 2. Folder structure

```
business-saathi/
├── backend/
│   ├── app/
│   │   ├── main.py              # creates the FastAPI app, serves frontend
│   │   ├── config.py            # reads environment variables
│   │   ├── database.py          # SQLite connection + table creation
│   │   ├── models.py            # table definitions
│   │   ├── schemas.py           # request/response validation (Pydantic)
│   │   ├── routes/              # orders.py, customers.py, products.py,
│   │   │                        # voice.py, dashboard.py, system.py
│   │   ├── repositories/        # database queries, one file per table group
│   │   ├── services/
│   │   │   ├── speech/          # base.py (interface), sarvam.py, audio.py (checks)
│   │   │   ├── extraction/      # base.py (interface), rules.py (default parser),
│   │   │   │                    # units.py, matcher.py (catalogue)
│   │   │   └── orders.py        # create/confirm/status rules, duplicate checks
│   │   └── demo_data.py         # clearly labelled sample data
│   ├── tests/                   # pytest tests
│   └── requirements.txt
├── frontend/
│   ├── index.html               # single page shell with sidebar
│   ├── css/styles.css
│   └── js/
│       ├── api.js               # all fetch() calls in one place
│       ├── router.js            # switches between pages
│       ├── recorder.js          # microphone recording
│       ├── components.js        # reusable cards, tables, status badges
│       └── pages/               # dashboard.js, voice-order.js, orders.js, ...
├── scripts/backup.sh, restore.sh
├── docs/ARCHITECTURE.md
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore                   # includes .env and data/
└── README.md
```

## 3. Database schema (SQLite)

Every table has `shop_id` so shops can be separated later (see risks, section 10).

**shops** — `id`, `name`, `created_at`

**customers** — `id`, `shop_id`, `name`, `phone` (optional), `notes`, `is_demo`, `created_at`, `updated_at`
- Index on (`shop_id`, `phone`) to spot duplicates.

**products** — `id`, `shop_id`, `name` (standard, e.g. "Rice"), `default_unit`, `price` (optional, empty = no price), `is_active`, `is_demo`, `created_at`, `updated_at`

**product_aliases** — `id`, `product_id`, `alias` (e.g. "chawal", "चावल", "chaval"), `language_code`
- Separate table because one product has many local names.

**orders** — `id`, `shop_id`, `order_number` (readable, e.g. BS-20261127-0007), `customer_id` (optional), `status` (draft / confirmed / pending / processing / completed / cancelled), `source` (voice / manual), `delivery_date` (optional), `delivery_time_text` (optional, e.g. "evening" — kept as words, never guessed into a clock time), `delivery_time` (optional, only if clearly stated), `special_instructions`, `transcription_id` (optional), `idempotency_key` (unique), `is_demo`, `confirmed_at`, `created_at`, `updated_at`

**order_items** — `id`, `order_id`, `product_id` (optional), `product_name_spoken` (as said), `product_name` (as saved), `quantity` (number, optional), `unit` (kg / g / l / ml / piece / packet, optional), `needs_review` (yes/no), `review_reason`

**transcriptions** — one per recording
- `id`, `shop_id`, `language_requested`, `language_detected`, `language_probability`, `duration_seconds`, `api_type` (rest / batch)
- `original_text`, `original_status`, `original_error`
- `roman_text`, `roman_status`, `roman_error`
- `english_text`, `english_status`, `english_error`
- `audio_path` (cleared when audio is deleted), `audio_delete_after`, `request_count`, `created_at`
- Each of the three outputs has its own status, so one failing does not erase the others.

**order_history** — `id`, `order_id`, `changed_at`, `field`, `old_value`, `new_value`
- Keeps edits and status changes, so the original transcript and earlier values are never lost.

Dates: stored as ISO (`2026-11-27`, timestamps in UTC); shown as DD-MM-YYYY in Asia/Kolkata.

## 4. Frontend pages

One HTML page; the sidebar swaps the content area (no page reloads).

| Page | What it shows / does |
|---|---|
| Dashboard | Welcome, search, language selector, stats (today, pending, completed, customers), voice panel, recent orders, pending orders |
| New Voice Order | Consent note, language selector, large mic button, timer, status, then 3 text boxes (original / Roman / English), editable order form, "Edit Order" and "Confirm and Save" |
| Manual order | Same editable form, no microphone (reachable from Dashboard and New Voice Order) |
| All Orders | Search, date filter, status filter, list, open/edit/cancel/change status |
| Pending Orders | All Orders pre-filtered to draft/confirmed/pending/processing |
| Order detail | Items, customer, delivery, transcripts, change history |
| Customers | List, search, add/edit, the customer's past orders |
| Order History | Completed and cancelled orders, searchable |
| Product Catalogue | Add/edit products, units, optional price, aliases |
| Settings | Shop name, default language, 12/24-hour time, audio retention, demo data on/off, Sarvam status (configured or not — never the key) |
| Help | How to use, privacy notice, language support table |

Design: forest green primary, warm off-white background, mint accent, charcoal text, white cards. Mobile-first: sidebar becomes a bottom/hamburger menu, buttons at least 48 px tall, nothing depends on hover.

## 5. Backend API design (REST, JSON)

| Method | Path | Purpose |
|---|---|---|
| GET | /api/health | App is running |
| GET | /api/system/status | Is Sarvam configured? Demo mode? Retention setting |
| GET | /api/languages | 23 languages with status: documented by Sarvam / tested by us |
| GET | /api/dashboard | Stats + recent + pending orders |
| GET | /api/orders | List with `q`, `status`, `date_from`, `date_to`, `customer_id`, `product` |
| POST | /api/orders | Create order (draft or confirmed). Requires `idempotency_key` |
| GET | /api/orders/{id} | One order with items, transcript and history |
| PUT | /api/orders/{id} | Edit order |
| POST | /api/orders/{id}/confirm | Explicit confirmation |
| PATCH | /api/orders/{id}/status | Change status (allowed moves only) |
| POST | /api/orders/{id}/cancel | Cancel |
| GET | /api/orders/{id}/possible-duplicates | Same customer + similar items recently |
| GET/POST | /api/customers | List/search, create |
| GET/PUT | /api/customers/{id} | View (with orders), edit |
| GET/POST | /api/products | List/search, create |
| PUT/DELETE | /api/products/{id} | Edit, deactivate |
| POST/DELETE | /api/products/{id}/aliases | Add/remove alias |
| POST | /api/voice/transcriptions | Upload audio + language → returns transcription record |
| GET | /api/voice/transcriptions/{id} | Status/results (used to poll batch jobs) |
| POST | /api/voice/transcriptions/{id}/retry | Retry only the outputs that failed |
| POST | /api/extract | Text → suggested order (works for typed text too, no API needed) |
| GET/PUT | /api/settings | Shop settings |
| POST | /api/demo/load, DELETE /api/demo | Load / remove labelled demo data |

Allowed status moves: draft → confirmed → pending → processing → completed; any non-completed → cancelled. Invalid moves return a clear 400 error.

## 6. Sarvam Saaras v4 integration (verified against docs)

**What the docs confirm**
- Endpoint: `POST https://api.sarvam.ai/speech-to-text`, header `api-subscription-key`, multipart form.
- Fields we will use: `file`, `model=saaras:v4`, `mode`, `language_code`, `keyterms`. Nothing else.
- Modes: `transcribe`, `translate`, `verbatim`, `translit`, `codemix`. **One mode per request** → three outputs need three requests.
- `language_code=unknown` (or omitted) → auto-detect; response gives `language_code` and `language_probability`.
- REST: audio up to **30 seconds**. Batch API: up to **2 hours per file**, job flow = create job → upload → start → poll → download. Docs suggest polling every ~5 s.
- `keyterms`: up to **50** terms, each up to **64 characters**, v4 only.
- Formats include WebM, OGG/Opus, MP4/M4A, WAV, MP3 — browser recordings (WebM on Chrome/Android, MP4 on iPhone Safari) are accepted.
- Errors: 400, 403, 429 (rate limit), 402 `insufficient_quota_error` (credits finished), 500, 503.
- Languages: 22 scheduled languages + English, all listed with codes (e.g. `hi-IN`, `brx-IN` Bodo, `sat-IN` Santali, `mni-IN` Manipuri, `doi-IN` Dogri).

**Our flow for one recording**
1. Browser records with MediaRecorder; shows timer; consent checkbox first.
2. Backend checks file type, size (limit 25 MB, our own setting) and real duration (measured with `ffprobe`, included in Docker image).
3. Audio saved to `/data/audio` with a transcription record **before** calling Sarvam (nothing is lost if the network drops).
4. ≤ 30 s → REST. > 30 s (we cap at 5 minutes for orders) → Batch.
5. Request 1: `mode=transcribe` (or `codemix` when "Mixed Hindi-English" is chosen) → **original text**. Saved immediately.
6. Request 2: `mode=translit` → **Roman text**. Request 3: `mode=translate` → **English**. Each saved separately with its own status.
7. Product catalogue names/aliases (top 50) are sent as `keyterms`.
8. Success → results stored; audio deleted per retention setting. Same audio is never sent again unless a specific output failed and the user taps Retry.

**Requests and cost per order** (Pay-as-you-go, ₹0.49 per audio-minute, billed per second, excl. GST)
- Requests per voice order: **3**. Each request is billed for the full audio length.
- 20-second order: 3 × 20 s = 60 s billed ≈ **₹0.49**.
- Sarvam gives ₹100 free credit on signup ≈ about 200 such orders. It is not free or unlimited.
- Rate limit (Pay-as-you-go): 60 REST requests/min, 20 batch requests/min — fine for one shop.
- Manual entry costs nothing.

**What is not automatic**: Saaras returns text only. Turning text into customer/products/quantities is our own extraction step (section 6b).

### 6b. Order extraction

Proposed for MVP: a **rule-based parser** (no extra API cost, works offline, easy to test):
- Finds numbers (digits and common Hindi/English number words), units (kilo/kg/gram/litre/packet/piece and variants), product words matched against the catalogue and its aliases, names before "ji ko / ke liye", phone numbers (10 digits), and delivery words (aaj/kal/shaam/subah/today/evening…).
- Runs on the original text and the Roman text; the English text is used only as a hint. The spoken product word is kept next to any catalogue match.
- Anything missing or unsure is left blank and marked "Needs review" with a reason. Nothing is invented; no price unless set in the catalogue.

Optional later upgrade: Sarvam chat model (`sarvam-105b`) with `response_format` JSON schema. It costs extra tokens and needs real testing, so it stays off by default behind a setting.

## 7. Docker setup

- One `Dockerfile`: `python:3.12-slim` + `ffmpeg` (for duration check) + app code. Runs `uvicorn` on port 8000.
- `docker-compose.yml`: one service `app`, port `8000:8000`, `env_file: .env`, named volume `saathi_data` mounted at `/data` (database + temporary audio). Restarting or rebuilding the container keeps the data.
- Backup: `scripts/backup.sh` copies the database safely (SQLite `.backup`) to `./backups/` with a date in the name; `restore.sh` puts one back. README will explain both.

## 8. Testing strategy

- **Automated (pytest, run every stage)**: start without key; create/save/retrieve/edit manual order; status rules; search and filters; idempotency (double Confirm creates one order); missing-key message; Sarvam errors (400/402/429/500/timeout/network) mocked so the app never crashes; original text kept when translit/translate fail; three outputs stored separately; extraction cases (multiple products, unclear quantity, unknown product, missing customer, missing delivery, Hinglish).
- **Docker test**: create orders → `docker compose restart` → orders still there.
- **Browser test**: desktop and mobile-sized screens.
- **Real Sarvam tests**: only possible once you provide a `SARVAM_API_KEY`. Each language becomes "tested" in the app only after a real recording passes. Until then it shows "documented by Sarvam, not yet tested".
- Rule: no test is reported as passed unless it was actually run.

## 9. Development milestones

| # | Stage | Result you can see |
|---|---|---|
| 1 | Project skeleton, Docker, database, health check | App opens in browser via Docker Compose |
| 2 | Products, customers, manual orders (backend + tests) | Orders saved in SQLite |
| 3 | Frontend: layout, dashboard, orders, customers, catalogue, settings | Full app usable without any API key |
| 4 | Demo mode, search/filters, status flow, duplicate protection, history | Judge-ready demo without voice |
| 5 | Rule-based extraction + review screen (from typed text) | Type an order → editable form |
| 6 | Recording + Sarvam REST (3 outputs, keyterms, errors, retry) | Real voice orders ≤ 30 s |
| 7 | Batch API for > 30 s, audio retention clean-up | Longer recordings |
| 8 | Backup/restore scripts, README, mobile polish, final test run | First demo ready |

## 10. Risks and limitations

- **Single shop for MVP**: tables have `shop_id`, but there is no login. Safe for a local/demo install, **not** for a public multi-shop website. Adding login is a later stage.
- **Cost doubles/triples with outputs**: three outputs = three billed requests per recording.
- **Rule-based extraction is limited**: works best for common patterns (Hindi/Hinglish/English). Other languages will mostly rely on the Roman and English text and need more manual correction.
- **Language testing**: Sarvam documents 23 languages; we can only honestly mark the ones we test with real recordings (likely Hindi, Hinglish and English first).
- **Browser microphone** needs HTTPS or `localhost`. On a phone over local Wi-Fi it may refuse to record without HTTPS.
- **Batch API is slower** (job + polling), so long recordings take longer.
- **No API key in this environment yet** — Sarvam features will be built and tested with mocks until you add a key.

## 11. Approved refinements (27-11-2026)

These rules override anything above that disagrees.

1. **Modular extraction.** `services/extraction/base.py` defines one interface: text in → suggested order + list of uncertain fields out. The rule-based extractor is the default and only implementation in the MVP. An AI-based extractor can be added later as a second implementation, switched on by a setting. No extra API cost by default.
2. **Original transcript is the source of truth.** Extraction runs on the original transcript. Roman and English text are only supporting references (for example, to confirm a number). An uncertain product or quantity is left as spoken, or left blank, and flagged "Needs review" — never replaced by a guess.
3. **Speech workflow.**
   - The original transcript is requested first and saved before anything else happens.
   - Transliteration and translation are separate steps with separate statuses; each can be retried on its own.
   - A step that already succeeded is never sent again. The audio's SHA-256 fingerprint is stored, so uploading the same recording again reuses the saved results instead of paying again.
   - Before processing, the screen shows: number of requests (normally 3) and estimated cost (duration × ₹0.49/min × requests, Pay-as-you-go, excl. GST). After processing it shows the actual requests made.
4. **Consent and retention are visible.** Before the first recording, the shopkeeper sees: "The audio is sent to Sarvam AI (India) to convert speech to text. Please tell the customer before recording." They must tick a consent box. The voice screen and Settings show the retention period (default 24 hours, configurable, 0 = delete right after processing). A background clean-up deletes expired audio files; transcripts stay.
5. **Single shop, local/demo only.** No login in this version. README and Settings state clearly: do not deploy publicly with real customer data until login and server-side access control are added.
6. **Demo vs real data.** Demo rows are stored with `is_demo = 1`. The UI shows a "DEMO" badge on every demo customer, order and product, a banner while demo data exists, and a one-click "Remove demo data". Dashboard numbers show how many are demo. Demo order numbers start with `DEMO-`. Demo data is never mixed into real phone numbers (fake numbers only).
7. **Code size check.** At the end, a script counts non-blank, non-comment lines of our own source (backend, frontend, tests reported separately; docs and dependencies excluded) to confirm at least 300 meaningful lines.
8. **Focused MVP.** No payments, UPI, GST/accounting, inventory, suppliers, delivery tracking, WhatsApp or chatbot features.
