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
pip install -r requirements-dev.txt   # runtime deps + pytest/ruff; use requirements.txt for runtime only
```

Copy `.env.example` to `.env` and fill in real values:

```sh
cp .env.example .env
```

```
DATABASE_URL=postgresql+psycopg2://postgres:<your_postgres_password>@localhost:5432/universe_dev
JWT_SECRET=<at least 32 bytes; generate with: python -c "import secrets; print(secrets.token_hex(32))">
UNIVERSE_API_USERNAME=operator          # used by the AI scripts' --camera-id mode
UNIVERSE_API_PASSWORD=<that user's password>
```

The API refuses to start if `DATABASE_URL` or `JWT_SECRET` is missing, or
if `JWT_SECRET` is shorter than 32 bytes (the HS256 minimum). Changing
`JWT_SECRET` logs everyone out; open dashboards return to the sign-in page
on their own.

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

# Wired to the backend (real settings + real alerts). Credentials come from
# UNIVERSE_API_USERNAME/PASSWORD in .env, or --api-username/--api-password.
python -m app.ai.prototypes.roi_loitering --source 0 --camera-id 1
python -m app.ai.prototypes.tamper_detection --source "rtsp://user:pass@192.168.1.64:554/stream1" --camera-id 2
python -m app.ai.prototypes.face_recognition --source 0 --camera-id 1      # UNKNOWN_FACE alerts
python -m app.ai.prototypes.camera_health --source 0 --camera-id 1         # live online/offline status
```

| Script | With `--camera-id` it... |
|---|---|
| `roi_loitering` | reads ROI + loiter threshold from Settings, raises `ROI_ENTRY` / `LOITERING` |
| `tamper_detection` | reads tamper thresholds from Settings, raises `TAMPER_COVERED` / `TAMPER_MOVED` / `TAMPER_DEFOCUSED` |
| `face_recognition` | raises `UNKNOWN_FACE` (at most once per `--alert-cooldown`, default 30s) |
| `camera_health` | reports online/offline via heartbeat (dashboard updates live), raises `CAMERA_OFFLINE` / `CAMERA_ONLINE`, retries a dead source every `--retry-seconds` |

Thresholds are configured per camera from the dashboard's Settings page
(`/settings`, admin-only to edit) and read when a script starts, so
restart a camera's scripts after changing them.

The scripts re-login automatically when their 8-hour token expires and
keep running if the backend is briefly unreachable (the failed alert is
logged as a warning).

**Webcams vs IP cameras:** on Windows a USB webcam can be opened by only
one process at a time, so run one script per webcam. RTSP IP cameras
accept several connections, so detection, tamper, and health scripts can
all run against the same camera.

## 5. Tests and checks

Backend (from `backend/`, needs PostgreSQL running; tests create and use
a separate `universe_test` database, never `universe_dev`):

```sh
python -m pytest              # API, auth/RBAC, review flow, WebSocket
python -m ruff check app tests
python -m ruff format --check app tests
```

Frontend (from `frontend/`):

```sh
npm run build    # type-check + production build
npm run lint
```

To poke the API by hand, import `http://127.0.0.1:8000/openapi.json` into
Postman, or use the `curl` examples in `/docs/api-reference.md`.
