# Setup: Fresh Clone to Running

Tested on Windows with Python 3.12, Node 24, PostgreSQL 17. Run these in
order -- each step depends on the one before it.

## 1. PostgreSQL

Install PostgreSQL 17 (service `postgresql-x64-17` running), then create
the dev database:

```sh
createdb universe_dev
```

(Or via `psql`: `CREATE DATABASE universe_dev;`)

## 2. Backend

```sh
cd backend
python -m venv venv
venv/Scripts/activate       # Windows; `source venv/bin/activate` on Linux/macOS
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in real values:

```sh
cp .env.example .env
```

```
DATABASE_URL=postgresql+psycopg2://postgres:<your_postgres_password>@localhost:5432/universe_dev
JWT_SECRET=<any long random string -- used to sign JWTs>
```

Apply migrations and seed dev data:

```sh
alembic upgrade head
python -m app.db.seed
```

The seed script is idempotent (safe to re-run) and creates:
- `admin` / `admin123` (role: admin)
- `operator` / `operator123` (role: security_operator)
- "Test Camera 1", "Test Camera 2"

Run the API:

```sh
venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Confirm it's up: `GET http://127.0.0.1:8000/` should return
`{"status": "ok", "service": "universe-backend"}`. Interactive API docs
are at `http://127.0.0.1:8000/docs`.

**Use `127.0.0.1`, not `localhost`**, when testing from a script or
browser on Windows -- see the note in `/docs/architecture.md` about the
IPv6 fallback delay.

## 3. Frontend

```sh
cd frontend
npm install
cp .env.example .env
```

`.env` should point at the backend started in step 2:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_WS_BASE_URL=ws://127.0.0.1:8000
```

```sh
npm run dev
```

Open the printed local URL (default `http://localhost:5173`), sign in
with `admin`/`admin123` or `operator`/`operator123`.

## 4. Running an AI script against a real camera

From `backend/`, with the venv active and the API running:

```sh
# Webcam, standalone (no backend wiring, prints to console only)
python -m app.ai.prototypes.roi_loitering --source 0 --headless

# Webcam or RTSP IP camera, wired to the backend (real settings + real alerts)
python -m app.ai.prototypes.roi_loitering --source 0 --camera-id 1 \
    --api-username operator --api-password operator123

python -m app.ai.prototypes.tamper_detection --source "rtsp://user:pass@192.168.1.64:554/stream1" \
    --camera-id 2 --api-username operator --api-password operator123
```

Thresholds (ROI box, loiter seconds, tamper sensitivity) are configured
per camera from the dashboard's Settings page (`/settings`, admin-only
to edit) -- they're read from the `camera_settings` table at script
startup, not hardcoded.

## 5. Running the test suite / Postman checks

No automated test suite exists yet (the project was verified module-by-
module per CLAUDE.md Section 12 -- see `/docs/evaluation-results.md`
for exact commands and results for every module). To manually re-verify
the API: import the running backend's OpenAPI schema
(`http://127.0.0.1:8000/openapi.json`) into Postman, or see
`/docs/api-reference.md` for a plain-text endpoint list with example
`curl` calls.
