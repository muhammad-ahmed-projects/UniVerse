# UniVerse — AI-Powered General-Purpose Smart Surveillance System

> Final Year Project, Department of Computer Sciences, Iqra University — Batch 2026
> This file is the single source of truth for this project. Read it fully at the
> start of every session before doing anything. Keep the "Current Status" checklist
> at the bottom updated as work progresses, instead of asking the team to re-explain
> the project each time.

## 1. Team & Supervision
- **Team:** Khawaja Shees Uddin (IU02-0123-0044), Aiman Shahid (IU02-0123-0343),
  Muhammad Ahmed (IU02-0121-0602)
- **Supervisor:** Dr. Noman Islam, Senior Lecturer, Computer Sciences
- **Domains:** Artificial Intelligence, Networking, Machine Learning
- **Nature:** New project (not industrial collaboration, not an extension)

## 2. Brief Outline
UniVerse is an AI-powered, general-purpose surveillance system designed for
companies, offices, warehouses, shops, and other organizations. It processes
camera feeds to detect and track people, recognize registered faces where
authorized, and identify security events such as suspicious loitering or
activity in restricted areas. It also monitors camera health and detects
possible tampering — including a person approaching very close to a camera,
touching, covering, or moving it, as well as a camera going offline, losing
its video feed, or losing power where a reliable status signal is available.
A centralized dashboard shows camera status, real-time alerts, and incident
records. The system will be demonstrated in a mock environment created by the
project team using its own cameras.

## 3. Objectives
- Build an AI-based system that processes live or recorded feeds from
  cameras installed by the project team or an organization.
- Detect faces and, where authorized, recognize registered individuals while
  distinguishing unknown/unregistered people.
- Detect and track multiple people across consecutive video frames using
  computer vision.
- Detect security events: suspicious loitering, entry into configured
  restricted regions, and unusual activity for human review.
- Develop a real-time dashboard showing camera feeds/status, detected
  people, alerts, and incident history.
- Detect possible camera tampering (close approach, touching, covering, or
  moving a camera) using visual changes and configurable rules.
- Detect camera health problems: loss of video feed, disconnection/offline
  status, and power loss where a reliable status signal is available.
- Provide configurable alert priorities, timestamps, camera identification,
  and incident acknowledgement/resolution.
- Implement incident management: recording, reviewing, acknowledging, and
  resolving security-related events.
- Evaluate detection/recognition performance, false alerts, FPS, processing
  latency, and camera-offline/tampering detection under different test
  conditions.

## 4. Scope
General-purpose AI surveillance solution for organizations. Includes:
camera-stream processing, face detection and authorized face recognition,
multi-person tracking, restricted-region monitoring, loitering and
suspicious-activity alerts, a dashboard for camera status and incidents,
camera-tampering detection (close approach/touch/cover/move), and
camera-health monitoring (offline, feed loss, power-loss where supported).
The team installs its own cameras and builds a controlled mock environment
for demonstration and evaluation.

**Out of scope (explicitly, unless the team later decides otherwise):**
student portal, AI chatbot, RAG knowledge base, examination-specific
surveillance — these appeared in an early Gantt-chart draft but are **not**
part of the approved written objectives/scope above. Do not build these
unless the team explicitly asks.

## 5. Proposed Methodology (this defines HOW to build it)
- **System Authentication:** Secure login + role-based access control
  (admin vs. security operator).
- **Camera & Video Processing:** OpenCV to connect to project-owned
  webcams/IP cameras or sample video; extract frames; preprocess; process
  feeds in real time.
- **Face Recognition:** Face detection + InsightFace/ArcFace embeddings with
  similarity thresholds to match registered faces; "unknown person" label
  when no reliable match.
- **Person Detection & Tracking:** An object-detection model (YOLO family)
  + multi-object tracking (MOT, e.g. DeepSORT/ByteTrack) to assign temporary
  tracking IDs across frames.
- **Suspicious Activity Detection:** Analyze video + tracked movement to
  flag predefined events for a security operator's review.
- **Restricted-Area Monitoring:** Configurable Regions of Interest (ROI);
  alert on entry/rule violations.
- **Loitering Detection:** Time a tracked person stays in a configured
  region; alert when a configurable threshold is exceeded.
- **Alert & Incident Management:** Centralized alert engine + REST APIs +
  PostgreSQL storing alerts, camera details, timestamps, evidence
  references, acknowledgement/resolution status.
- **Camera Tampering Detection:** Sudden scene changes, obstruction/covered
  lens patterns, camera movement, close approach — tuned in the mock
  environment to reduce false alerts.
- **Camera Health Monitoring & System Implementation:** Heartbeat/
  connectivity checks + stream-read status, via FastAPI backend +
  React/TypeScript dashboard + PostgreSQL + WebSockets for live status/alerts.
  Power-loss detection where a supported signal exists.
- **Testing & Evaluation:** Precision, recall, F1 where applicable,
  face-match errors, false-alert rate, FPS, latency, camera-offline
  detection, tampering-alert performance — under controlled test scenarios.
- **Security & Privacy:** Role-based access, password hashing, audit logs,
  configurable retention, restricted access to face data, human review
  before an AI alert is treated as a confirmed incident.

## 6. Tech Stack (fixed per proposal — don't swap without discussion)
- **Backend:** Python, FastAPI, PostgreSQL, WebSockets
- **Frontend:** React, TypeScript, Tailwind CSS — built on the **TailAdmin**
  free dashboard template (reuse its layout/cards/tables/charts rather than
  building UI from scratch)
- **Computer Vision / AI:** OpenCV; pretrained face-detection/recognition
  model (InsightFace/ArcFace); pretrained person-detection model (YOLO
  family); multi-object tracking (DeepSORT/ByteTrack); visual-anomaly/
  tampering-analysis approach
- **Dev tools:** VS Code, Git/GitHub, Postman

## 7. Resources
- **Hardware:** Dev laptop/PC (optional GPU), project-team-owned webcams/IP
  cameras, basic network/power equipment for demo.
- **Data:** Team's own mock surveillance environment; own-collected footage;
  consent-based face registration; no external/real CCTV data needed.
- **People:** Team members split across AI/ML, frontend, backend, database,
  camera setup, integration, testing, privacy, documentation.

## 8. Final Deliverables
1. General-purpose AI surveillance platform: person detection/tracking +
   authorized face recognition
2. Real-time dashboard: camera status, detected events, alert priorities,
   incident review/resolution
3. Security-event detection: loitering, restricted-region entry, predefined
   unusual activity
4. Camera protection & health monitoring: close approach, touch/cover/move,
   offline, feed loss, power-loss (where supported)
5. Controlled mock-environment demo, performance evaluation, setup
   instructions, final technical documentation

## 9. Repo Structure (target)
```
/backend
  /app
    /api          → FastAPI route handlers (auth, cameras, alerts, incidents, people)
    /models        → SQLAlchemy models (Camera, Alert, Incident, User, Person)
    /services      → business logic (detection, tracking, recognition, tamper, health)
    /ai            → YOLO, InsightFace, tracking wrapper modules
    /db            → session, Alembic migrations
    main.py
  requirements.txt
/frontend            → TailAdmin (React+TS+Tailwind) adapted for:
                        Dashboard, Camera Feeds, Alerts, Incidents,
                        Registered People, Settings/Auth
/docs                → architecture notes, API docs, evaluation results
CLAUDE.md            → this file
```

## 10. Working Instructions for Claude Code
- Work in **small, testable increments** — one module at a time; confirm it
  runs before moving to the next.
- Start with a **standalone AI prototype** (webcam → person detection,
  bounding boxes shown) before touching backend/frontend. Validate AI
  pieces work before wiring into FastAPI.
- Use **pretrained models** (e.g. YOLOv8n/s, InsightFace buffalo_l) — do
  not train from scratch unless explicitly asked.
- Adapt **TailAdmin's existing components** for the frontend instead of
  writing new UI from zero.
- Briefly narrate new AI/backend concepts (the team is frontend-strong,
  learning backend/AI) — but don't over-explain React/TS/Tailwind basics.
- After each working piece, suggest the next logical step.
- For irreversible/tradeoff decisions (tracking library, auth approach,
  etc.), briefly explain options and recommend one rather than picking
  silently.
- Keep commits small, with clear messages.
- Anything resembling "student chatbot / RAG / student portal" is **out of
  scope** per the approved proposal — flag it rather than building it.
- **Never mark an item "done" in the status checklist without it passing
  its own test first** (see Section 12). "Looks right" is not "done".

## 11. Coding Standards & Best Practices (non-negotiable)

### General
- Follow the repo structure in Section 9 — don't dump files at the root or
  invent a different layout mid-project.
- One concern per file/module (e.g. tracking logic stays out of API route
  handlers; DB models stay out of service logic).
- No hardcoded secrets, API keys, DB passwords, or camera credentials in
  code — use a `.env` file (gitignored) + `.env.example` committed with
  placeholder values.
- Every new dependency goes into `requirements.txt` (backend) or
  `package.json` (frontend) immediately — never left as an untracked
  "pip install I ran once."
- Write docstrings/comments for non-obvious logic (tracking math, tamper
  thresholds, similarity scoring) — not for self-explanatory code.

### Backend (Python/FastAPI)
- Follow PEP 8. Use type hints everywhere (`def foo(x: int) -> bool:`).
- Pydantic models for all request/response schemas — no raw dicts across
  API boundaries.
- Central error handling via FastAPI exception handlers — endpoints should
  not leak raw stack traces to the client.
- All DB access through SQLAlchemy sessions/Alembic migrations — no raw SQL
  strings unless unavoidable, and never string-concatenated (SQL-injection
  risk).
- Input validation on every endpoint (camera IDs, thresholds, file
  uploads) — never trust client input directly.
- Passwords hashed (bcrypt/argon2) — never stored or logged in plaintext.

### Frontend (React/TypeScript)
- Strict TypeScript — no `any` unless truly unavoidable, and justified in
  a comment when used.
- Functional components + hooks (no class components).
- API calls isolated in a `/services` or `/api` layer — components don't
  call `fetch`/`axios` directly inline.
- Loading, empty, and error states handled explicitly in every data-driven
  view (camera list, alerts list, etc.) — no silent blank screens.
- Reuse TailAdmin's existing component patterns/styling conventions rather
  than introducing a second, inconsistent style system.

### AI/Computer Vision modules
- Keep model-loading code separate from per-frame inference code (load
  once, reuse — don't reload a model every frame).
- Make thresholds (face-match similarity, loitering time, tamper
  sensitivity) **configurable**, not hardcoded magic numbers — per the
  proposal's "configurable rules" requirement.
- Log FPS/latency during development so performance regressions are caught
  early, not only at the final evaluation stage.

### Git workflow
- Small, focused commits with clear messages (what + why, not just "fix").
- Don't commit generated/large files (model weights, `node_modules`,
  `venv`, `.env`) — use `.gitignore`.
- Before marking a feature "done," it should run cleanly from a fresh
  clone (no "works on my machine only" steps left undocumented).

## 12. Testing Requirements (every module needs this before "done")
Nothing in Section 13's checklist is checked off until it has a matching
test/verification per this table:

| Module | How it must be verified before marking done |
|---|---|
| Person detection | Run on a recorded test clip + live webcam; confirm bounding boxes are stable, note approximate FPS |
| Tracking | Confirm IDs stay consistent as a person moves/partially occludes across frames; count ID switches |
| Face recognition | Test with 3+ registered faces + 2+ unknown faces; record true/false match rate at the chosen threshold |
| Loitering detection | Time a person staying in a zone past the threshold; confirm alert fires once, not repeatedly spammed |
| Restricted-area (ROI) | Confirm alert fires on entry, not on false triggers from nearby movement |
| Camera tamper detection | Test cover/move/defocus manually; confirm each triggers the correct alert type |
| Camera health monitoring | Unplug/disconnect a camera; confirm offline status is detected within a reasonable time |
| Backend API endpoints | Test with Postman (happy path + invalid input) before frontend integration |
| WebSocket alerts | Confirm dashboard receives a new alert in real time without a page refresh |
| Auth / RBAC | Confirm admin vs. security-operator roles actually restrict access, not just hide UI elements |
| Full integration | Run end-to-end: camera → detection → alert → dashboard → acknowledge/resolve, with no manual DB edits |

Write these results into `/docs/evaluation-results.md` as they're done —
this feeds directly into the proposal's required "Testing & Evaluation"
deliverable (precision/recall/F1, false-alert rate, FPS, latency).

## 13. Step-by-Step Execution Plan (follow this order)

Each phase ends only when its own deliverable actually runs and is verified
per Section 12's testing table — don't move to the next phase on
"should work."

### Phase 0 — Setup (foundation, do this first)
1. Create the repo structure from Section 9.
2. Backend: Python virtual environment, install FastAPI, SQLAlchemy,
   Alembic, psycopg2/asyncpg, python-dotenv, uvicorn.
3. Frontend: drop TailAdmin into `/frontend`, `npm install`, confirm it
   runs locally unmodified first (`npm run dev`) before any customization.
4. PostgreSQL: install locally (or Docker container), create the dev
   database, confirm connection from a throwaway script.
5. `.env.example` + `.gitignore` (venv, node_modules, .env, model weights,
   __pycache__) committed first, before any real code.
6. Initial commit: empty-but-running skeleton (backend "hello world"
   endpoint + frontend default TailAdmin page + DB connects).

### Phase 1 — AI Core Prototypes (standalone, no backend/frontend yet)
Build and verify each of these as an isolated script before any
integration — this is the highest-risk part of the project, so it goes
first and gets validated on its own.
1. Person detection: webcam → YOLO → bounding boxes drawn on screen.
2. Tracking: wrap detection with DeepSORT/ByteTrack → stable IDs per
   person across frames.
3. Face recognition: register 2-3 team members' faces → recognize
   live/known vs. unknown on webcam feed.
4. Restricted-area (ROI) logic: define a zone in the frame → flag when a
   tracked person's position enters it.
5. Loitering logic: track how long an ID stays inside a zone → flag past
   a configurable threshold.
6. Camera tamper detection: frame-difference/edge-based checks for
   covered, moved, and defocused states.
7. Camera health check: detect feed loss / disconnect via OpenCV read
   failures or stream timeout.

Deliverable: a single local script (or small set of scripts) demonstrating
all seven behaviors against the webcam, each one individually testable.

### Phase 2 — Data Layer
1. Design PostgreSQL schema: `users`, `cameras`, `people` (registered
   faces), `face_embeddings`, `alerts`, `incidents`.
2. Alembic migrations for the schema — never hand-edit the DB directly.
3. Seed script for dev data (a couple of test cameras, test users).

### Phase 3 — Backend API
1. Auth: register/login, password hashing, JWT (or session) issuance,
   role-based access control (admin vs. security operator).
2. CRUD endpoints: cameras, registered people, alerts, incidents.
3. Wire Phase 1's AI scripts into backend services (`/app/services`,
   `/app/ai`) — triggered per camera stream, writing alerts to DB instead
   of just printing/drawing locally.
4. WebSocket endpoint broadcasting new alerts/camera-status changes in
   real time.
5. Test every endpoint in Postman (happy path + bad input) before touching
   the frontend.

### Phase 4 — Frontend Dashboard (on TailAdmin)
1. Auth pages (login) wired to the real backend — not mock data.
2. Camera list/status page (live via WebSocket).
3. Alerts feed (live, with priority/type/timestamp).
4. Incident detail view: acknowledge/resolve flow.
5. Registered-people management page (add/remove faces).
6. Settings: ROI configuration, loitering threshold, tamper sensitivity —
   configurable from the UI, not just hardcoded in Python.

### Phase 5 — Integration
1. Run the full pipeline end-to-end: camera → AI detection → alert → DB →
   WebSocket → dashboard → operator acknowledges/resolves — no manual DB
   edits anywhere in that chain.
2. Fix cross-module bugs surfaced only when everything runs together
   (timing, race conditions, stale state).

### Phase 6 — Testing & Evaluation (maps to the proposal's required deliverable)
1. Run the full Section 12 testing table; record results.
2. Measure and document: detection/recognition accuracy, false-alert rate,
   FPS, processing latency, camera-offline detection time, tamper-alert
   accuracy — under the team's controlled mock-environment conditions.
3. Security/privacy pass: confirm RBAC actually restricts access, confirm
   passwords are hashed not plaintext, confirm face data access is
   restricted, confirm there's human review before an alert becomes a
   "confirmed incident."

### Phase 7 — Documentation & Demo
1. `/docs`: architecture overview, setup instructions (fresh-clone-to-
   running), API reference, evaluation results.
2. Prepare the mock-environment demo (team's own cameras) matching the
   proposal's "Final Outcomes/Deliverables."
3. Final report + presentation materials.

## 14. Current Status
- [x] Environment setup (Python 3.12 venv, Node 24, PostgreSQL 17, repo
  structure) — backend health endpoint returns 200, `universe_dev` DB
  created and reachable via SQLAlchemy, frontend `npm run dev` returns 200
- [x] TailAdmin template integrated as frontend base — runs unmodified,
  no customization yet
- [x] Person detection prototype (YOLO + webcam) — see
  `/docs/evaluation-results.md`; ~6 FPS (clip) / ~4.3 FPS (live webcam) on
  CPU with YOLOv8n, stable boxes on recorded clip + live webcam
- [ ] Face recognition prototype (InsightFace)
- [ ] Tracking (DeepSORT/ByteTrack) merged with detection
- [ ] Restricted-area (ROI) + loitering logic
- [ ] Camera tamper detection (covered/moved/defocused)
- [ ] Camera health monitoring (offline/feed loss/power loss)
- [ ] PostgreSQL schema + backend API (auth, cameras, alerts, incidents)
- [ ] WebSocket real-time alerts
- [ ] Frontend dashboard pages wired to backend
- [ ] Integration testing (FPS, latency, false-alert rate, accuracy)
- [ ] Documentation + demo environment setup

Update this checklist as each item is completed.
