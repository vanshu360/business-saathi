# Business Saathi

A multilingual, voice-first order assistant for small Indian shops: speak an order, check it, save it.

> **Status:** under construction, built milestone by milestone. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
> This version is **single-shop and for local/demo use only**. It has no login. Do not put it on the public internet with real customer data.

## Run with Docker Compose

```bash
cp .env.example .env          # optional: add SARVAM_API_KEY here
docker compose up --build
```

Open http://localhost:8000. The app works without a Sarvam key (manual entry only).

Stop with `Ctrl+C` or `docker compose down`. Your data is kept in the Docker volume `saathi_data`, so it survives restarts.
(`docker compose down -v` **deletes** the volume and all data.)

## Run without Docker (for development)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Data is stored in `./data/business_saathi.db`.

## Run the tests

```bash
cd backend
source .venv/bin/activate
pytest
```
