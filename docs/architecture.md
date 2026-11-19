# Architecture Overview

UniVerse is a general-purpose AI surveillance platform: cameras feed
video to standalone AI scripts, which detect people and security events
and report them to a central backend, which a real-time dashboard
displays to a human operator for review.

## Components

```
Camera (webcam / RTSP IP camera)
        |
        v
AI scripts (backend/app/ai/prototypes/)
  person_detection.py   -- YOLOv8n, person-class detections
  tracking.py           -- YOLOv8n + ByteTrack, per-person IDs
  face_recognition.py   -- InsightFace buffalo_l, known/unknown faces
  roi_loitering.py       -- restricted-area entry + loitering alerts
  tamper_detection.py    -- covered/moved/defocused camera state
  camera_health.py       -- feed-loss / offline detection
        |
        | backend_client.py (requests): GET camera_settings + face-embeddings,
        | POST alert + evidence images, POST heartbeat, POST live frames,
        | POST face sightings (frames/images/sightings on a background thread)
        v
FastAPI backend (backend/app/)
  api/        -- route handlers (auth, cameras, people, alerts, incidents, ws)
  models/     -- SQLAlchemy ORM models
  schemas/    -- Pydantic request/response models
  services/   -- ws_manager (WebSocket broadcast), frame_store (latest live
                 frame per camera), face_encoder (InsightFace for dashboard
                 registration), media_store + images (evidence/face files),
                 retention (evidence clean-up)
  db/         -- session + Alembic migrations
        |
        | REST (JWT-authenticated) + 2 WebSockets (/ws/alerts, /ws/stream)
        v
PostgreSQL                         React/TypeScript dashboard (frontend/)
  users, cameras, people,            built on TailAdmin, talks to the
  face_embeddings, alerts,           backend only through frontend/src/services/*.ts
  alert_images, incidents,           (no inline fetch in components)
  camera_settings
Files: backend/media/ (MEDIA_DIR)  evidence JPEGs + face thumbnails, gitignored
```

## Why AI scripts are separate processes, not in-process with the API

Each detection/tracking/tamper/health script in `app/ai/prototypes/` is
a standalone Python process (`python -m app.ai.prototypes.<script>
--camera-id <id> ...`), one per camera feed, rather than code running
inside the FastAPI event loop. Reasons:
- Model inference (YOLO, InsightFace) is CPU-bound and blocking; running
  it inside FastAPI's async event loop would stall every other request
  while a frame is being processed.
- A crash or hang in one camera's detection loop can't take down the API
  or any other camera's processing.
- Each script can be developed, tested, and run completely standalone
  (see `/docs/evaluation-results.md` -- every script was verified on its
  own against a webcam before any backend integration existed).

An admin normally starts them from the dashboard (Cameras or Live View >
Monitoring): `services/camera_runner.py` launches the chosen scripts as
child processes with the camera's saved stream source and `--headless`,
keeps the last 200 lines of their output for the dashboard's Script
output panel, and stops them on request or when the API shuts down. They
stay separate processes, so everything above still holds: a crashing
script only marks its camera offline and shows its error in the log. A
USB webcam (source `0`, `1`, ...) gets one script at a time, because
Windows lets only one process open it. They can also still be started
by hand from a terminal.

They talk to the backend the same way the dashboard does: authenticated
REST calls (`backend/app/ai/prototypes/backend_client.py` -- login once,
`GET /cameras/{id}/settings` for thresholds, `POST /alerts` for events).
This means an alert posted by an AI script goes through the exact same
validation and WebSocket broadcast as the dashboard's own alerts, with
no separate code path to keep in sync.

## Data flow for one detection event

1. AI script reads a frame from its camera (webcam index or RTSP URL
   passed via `--source`).
2. It detects/tracks/classifies against thresholds loaded once at
   startup from `GET /cameras/{id}/settings` (not hardcoded).
3. On a state-changing event (ROI entry, loitering, unusual activity,
   tamper state change), it calls `POST /alerts`.
4. The backend validates `camera_id` and `priority`, writes the `Alert`
   row, and broadcasts a `{"type": "alert", ...}` JSON message to every
   connected `/ws/alerts` WebSocket client.
5. The dashboard's `useAlertsSocket` hook receives that broadcast and
   updates the open page live, no refresh. Each browser tab keeps one
   shared WebSocket for all its components, reconnecting with
   exponential backoff (1s up to 30s) after a drop.
6. A human operator reviews the alert: "Real" or "False alarm"
   (`PATCH /alerts/{id}/review`), and, if it's a real incident,
   clicks "Create Incident" (`POST /incidents`, linking back via
   `source_alert_id`) -- alerts never auto-promote themselves. This is
   the project's required human-review step before an AI alert counts
   as a confirmed incident.
7. The operator acknowledges, then resolves the incident
   (`PATCH /incidents/{id}/acknowledge`, `PATCH /incidents/{id}/resolve`),
   each broadcasting an `incident_update` WebSocket message.

See `/docs/evaluation-results.md` ("Phase 5 -- Full-pipeline
integration") for this entire chain verified end-to-end with a real
webcam and a real browser tab.

Camera health follows the same path: `camera_health.py` posts
`online`/`offline` to `POST /cameras/{id}/heartbeat`, which updates
`cameras.status`/`last_seen_at` and broadcasts `camera_status` only when
the status actually changes; the script also raises `CAMERA_OFFLINE` /
`CAMERA_ONLINE` alerts on transitions.

## Live view

The backend never opens a camera itself (a USB webcam can only be opened
by one process, and that's the AI script). Instead, every script run with
`--camera-id` hands its annotated frame (boxes, track IDs, names, ROI zone)
to `backend_client.py`, whose background thread downscales it to 640 px,
encodes a JPEG and posts it to `POST /cameras/{id}/frame` about 5 times a
second (`--stream-fps`). The backend keeps only the latest frame per
camera in memory (`services/frame_store.py`), never on disk.

The dashboard's Live View page opens one `/ws/stream` WebSocket, subscribes
to every camera, and gets each new frame as a binary message (camera ID +
JPEG). One socket for all cameras matters: browsers allow ~6 HTTP
connections per host, so one MJPEG stream per camera would starve the
dashboard's API calls. A tile shows "No live feed" until a script streams
that camera, and "Feed stopped" if frames stop for 5 s.

If several scripts run on one IP camera, one owns the view: a detection
script (priority 1) wins over `camera_health` (priority 0, raw frames),
and between equals the first keeps it until it's silent for 3 s.

## Evidence images

When a script raises an alert, `backend_client.py` attaches the next 3
annotated frames, one per second (`--evidence-frames`,
`--evidence-interval`), via `POST /alerts/{id}/images`. The backend
re-encodes each upload to JPEG (which also strips metadata), stores it
under `MEDIA_DIR/evidence/` with a generated file name, and broadcasts
`alert_image` so open Alerts/Incidents pages add the thumbnail live. An
incident shows the evidence of the alert it was promoted from.

Retention (proposal: "configurable retention"): images older than
`EVIDENCE_RETENTION_DAYS` (default 30) are deleted at startup and every 6
hours, along with files whose alert no longer exists.

## Face registration and recognition

1. An admin registers a person on the Registered People page (name plus a
   consent checkbox), then adds 3-5 face photos by upload or the browser
   camera.
2. `POST /people/{id}/faces` runs InsightFace (`buffalo_l`, the same model
   the recognizer uses) in the backend. The photo must contain exactly one
   face. If none is found, the encoder retries with a border around the
   image, because the detector misses tightly cropped passport-style
   photos. The 512-d embedding goes into `face_embeddings` and a cropped
   thumbnail into `MEDIA_DIR/faces/`.
3. `face_recognition.py --camera-id N` downloads every active person's
   embeddings (`GET /face-embeddings`) and refreshes them every 30 s, so
   new registrations work without a restart. A face matches the person
   whose best sample scores highest, if that score reaches the camera's
   `face_match_threshold` (Settings page); otherwise it's "Unknown".
4. A match is reported via `POST /people/{id}/sightings` (at most every
   10 s per person), which updates the person's "last seen" camera and
   time on the People page live. Unknown faces raise `UNKNOWN_FACE` alerts
   with evidence. The names are also drawn on the live view.

## Unusual activity

`roi_loitering.py` also runs `activity_rules.py` on the tracked boxes of
each frame. The rules are a pure module (no camera, no model), so they are
unit-tested with synthetic tracks:

| Alert | Rule | Setting (`0` = off) |
|---|---|---|
| `CROWD` | At least N people in view. Fires once, re-arms when the count drops below N. | `crowd_threshold` (5) |
| `RUNNING` | A person's box centre moves faster than this, in frame widths per second, measured over about 1 s. | `running_speed` (0.6) |
| `FALL_DETECTED` | A person who was standing (box height > 1.3 x width) in the last 3 s stays lying (width > 1.2 x height) this long. | `fall_seconds` (2) |
| `ABANDONED_OBJECT` | A backpack, handbag or suitcase (YOLO COCO classes 24, 26, 28) stays still, with no person within 15% of the frame width, this long. | `abandoned_seconds` (30) |

These are heuristics on bounding boxes, not pose or action models: a fall
is detected from the box shape only, so someone lying down on purpose, or
a person seen side-on very close to the camera, can also trigger it. That
is why every one of these alerts goes to a person for review.

## Alert review and accuracy

Every alert can be marked "Real" or "False alarm" on the Alerts page.
Promoting it to an incident also marks it real. `GET /alerts/review-stats`
turns these verdicts into precision (real / reviewed) and false-alarm rate
(false alarms / reviewed), overall and per alert type. This is the
proposal's false-alert measurement, taken from the operators' own reviews
in the mock environment.

## Audit log

`services/audit.py` gives route handlers an `Auditor` (FastAPI
dependency) that adds an `audit_logs` row to the request's own database
session, so the entry is committed together with the change it records,
or not at all. Failed sign-ins and face-photo views are committed on their
own. Each row stores the action, the user and a snapshot of their
username, the target, a small JSON of details (never passwords) and the
client IP. Only admins can read it (`GET /audit-logs`, Audit Log page),
and there is no API to change or delete entries.

## Request handling

Route handlers are plain (sync) `def` functions because SQLAlchemy here
is synchronous; FastAPI runs them in its threadpool, so a slow query
can't stall the event loop that serves every other request and all open
WebSockets. Broadcasts are queued with `BackgroundTasks` and sent after
the DB commit. Promote/acknowledge/resolve take a row lock
(`SELECT ... FOR UPDATE`) so concurrent operators can't double-act on
the same alert or incident.

## Auth / RBAC

JWT (HS256, 8h expiry) issued by `POST /auth/login`. Every protected
route depends on `get_current_user` (any authenticated user) or
`require_role(UserRole.ADMIN)` (admin-only writes: creating/updating/
deleting cameras, people, and camera_settings; registering new user
accounts). The restriction is enforced server-side in the dependency,
not just hidden in the UI -- a `security_operator` token gets a real
`403` from the API for an admin-only route.

The AI scripts log in as `ai_service`, a service-account role. Face data
is the most restricted: face photos and thumbnails are admin-only, and
face embeddings can be read only by `admin` and `ai_service`, never by a
security operator.

The WebSocket handshake also checks that the token's user still exists
and is active. In the dashboard, any `401` clears the stored token and
returns the user to the sign-in page (`UNAUTHORIZED_EVENT` in
`api-client.ts`); a dropped WebSocket re-checks the session over HTTP
before reconnecting, so a revoked or expired token can't leave a tab
retrying forever. Camera stream credentials are masked in every API
response.

## Known constraints

- Single-process state: the WebSocket broadcast (`ws_manager.py`), the
  live frames (`frame_store.py`) and the monitoring runners
  (`camera_runner.py`) are in memory, so they only work with a single
  backend process. Monitoring doesn't survive an API restart; start it
  again from the dashboard. A multi-worker deployment would need a
  pub/sub broker (e.g. Redis) -- out of scope for this FYP's
  single-instance mock-environment demo.
- Face recognition is CPU-bound: about 1 frame per second with one face
  on the team's laptop, slower with several faces in view, so its live
  view updates slowly. Detection-only scripts run ~4-6 FPS.
- `face_recognition.py --register` (without `--camera-id`) still writes the
  old local `face_db/embeddings.pkl` for standalone experiments; faces
  registered that way are not visible to the dashboard or to the
  backend-wired recognizer.
- Detection scripts read their thresholds once at startup; changing
  Settings needs a script restart to take effect.
- Use `127.0.0.1`, not `localhost`, for the API base URL in local dev on
  Windows -- `localhost` resolves to IPv6 first, which the backend isn't
  listening on, adding a ~2s connection delay per request (see
  `/docs/evaluation-results.md`, "Phase 5 step 2").
