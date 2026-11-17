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
        | backend_client.py (requests): GET camera_settings, POST alert
        v
FastAPI backend (backend/app/)
  api/        -- route handlers (auth, cameras, people, alerts, incidents, ws)
  models/     -- SQLAlchemy ORM models
  schemas/    -- Pydantic request/response models
  services/ws_manager.py -- in-memory WebSocket broadcast
  db/         -- session + Alembic migrations
        |
        | REST (JWT-authenticated) + WebSocket
        v
PostgreSQL                         React/TypeScript dashboard (frontend/)
  users, cameras, people,            built on TailAdmin, talks to the
  face_embeddings, alerts,           backend only through frontend/src/services/*.ts
  incidents, camera_settings         (no inline fetch in components)
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
3. On a state-changing event (ROI entry, loitering, tamper state
   change), it calls `POST /alerts`.
4. The backend validates `camera_id` and `priority`, writes the `Alert`
   row, and broadcasts a `{"type": "alert", ...}` JSON message to every
   connected `/ws/alerts` WebSocket client.
5. The dashboard's `useAlertsSocket` hook (any open tab, any page)
   receives that broadcast and updates its alert list live, no refresh.
6. A human operator reviews the alert and, if it's a real incident,
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

## Auth / RBAC

JWT (HS256, 8h expiry) issued by `POST /auth/login`. Every protected
route depends on `get_current_user` (any authenticated user) or
`require_role(UserRole.ADMIN)` (admin-only writes: creating/updating/
deleting cameras, people, and camera_settings; registering new user
accounts). The restriction is enforced server-side in the dependency,
not just hidden in the UI -- a `security_operator` token gets a real
`403` from the API for an admin-only route.

## Known constraints

- Single-process `ConnectionManager` (`app/services/ws_manager.py`):
  WebSocket broadcast is in-memory, so it only works correctly with a
  single backend process. A production multi-worker deployment would
  need a pub/sub backend (e.g. Redis) instead -- out of scope for this
  FYP's single-instance mock-environment demo.
- Face embeddings are stored in a gitignored local pickle file
  (`backend/app/ai/prototypes/face_db/embeddings.pkl`), not the
  `face_embeddings` DB table yet -- the table exists in the schema but
  `face_recognition.py` doesn't write to it yet.
- Use `127.0.0.1`, not `localhost`, for the API base URL in local dev on
  Windows -- `localhost` resolves to IPv6 first, which the backend isn't
  listening on, adding a ~2s connection delay per request (see
  `/docs/evaluation-results.md`, "Phase 5 step 2").
