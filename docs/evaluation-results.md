# Evaluation Results

Results are recorded here as each module from CLAUDE.md Section 12's testing
table is verified. This feeds the proposal's required Testing & Evaluation
deliverable.

## Person Detection (Phase 1, step 1)

**Module:** `backend/app/ai/prototypes/person_detection.py` — YOLOv8n
(pretrained, COCO weights), person class only, configurable confidence
threshold (default 0.5).

**Test 1 — logic validation on known images** (`ultralytics` bundled
assets, not part of the actual deliverable, just a sanity check before
hardware testing):
- `bus.jpg` (3 visible people): 3/3 detected, confidences 0.83-0.87.
- `zidane.jpg` (2 visible people): 2/2 detected.
- Bounding boxes tight around each person, no false positives on the bus
  or background.

**Test 2 — recorded test clip** (6s, captured from the team's own
webcam, 170 frames, CPU inference):
- Person detected in every sampled frame (frames 0, 20, 40, ..., 160).
- Confidence stable: 0.88-0.89 across sampled frames.
- Bounding box stable (no jitter/drift) across the clip.
- Throughput: 170 frames in 28.4s -> **avg 6.0 FPS end-to-end** (capture +
  inference, CPU only, YOLOv8n).

**Test 3 — live webcam** (80 frames, direct `cv2.VideoCapture(0)`):
- Person detected consistently, confidence up to 0.94.
- Bounding box stable across sampled frames.
- Throughput: 80 frames in 18.5s -> **avg 4.3 FPS end-to-end**; inference-only
  step (model.predict call, excluding frame capture/display overhead)
  measured ~7.5 FPS.

**Notes:**
- All inference above ran on CPU (no GPU used). FPS numbers will improve
  with a GPU or a smaller/quantized model if real-time performance becomes
  a bottleneck once this is wired into the multi-camera backend pipeline.
- Confidence threshold, model weights path, and source (webcam index or
  video file) are all CLI-configurable, not hardcoded, per Section 11's
  coding standards.

**Verdict:** PASS — bounding boxes are stable on both a recorded clip and
live webcam, per Section 12's testing requirement for this module.

## Tracking (Phase 1, step 2)

**Module:** `backend/app/ai/prototypes/tracking.py` — YOLOv8n detection +
Ultralytics' built-in ByteTrack (`model.track(..., persist=True)`), person
class only. Chosen over DeepSORT: no extra appearance-embedding model to
run, since CPU inference is already the bottleneck (~6-7 FPS from the
detection-only prototype); ByteTrack is motion/IoU-based and ships with
`ultralytics` already (auto-installed its one extra dependency, `lap`,
needed for the Hungarian-algorithm assignment).

**Test 1 — recorded test clip** (10s, team's own webcam, 290 frames):
- Single person present throughout. Track ID assigned once (`ID 1`) and
  held for the entire clip — **0 ID switches** across 290 frames.
- Confidence on the tracked box: 0.88 (start) -> 0.94 (end).
- Throughput: 290 frames in 61.5s -> **avg 4.7 FPS end-to-end** (includes
  one-time ~10s auto-install of the `lap` dependency on first run).

**Test 2 — live webcam** (60 frames):
- Same result: single ID (`ID 1`) held for all 60 frames, 0 switches.
- Throughput: 60 frames in 13.5s -> **avg 4.4 FPS end-to-end**.

**Notes:**
- Both tests used a single person in frame (no multi-person or
  occlusion scenario yet) — confirms ID *stability* over time, not
  ID *re-acquisition* after occlusion/exit-reentry. ByteTrack is expected
  to assign a **new** ID if a person fully leaves the frame and re-enters
  (no appearance re-identification) — this is expected behavior, not a
  bug, and should be tested explicitly with multiple people / an
  occlusion scenario before Phase 6's full evaluation pass.
- Tracker config (`bytetrack.yaml` vs `botsort.yaml`), confidence
  threshold, and source are CLI-configurable.

**Verdict:** PASS for ID stability (0 switches on a continuously-visible
person, recorded clip + live webcam). Multi-person/occlusion re-test
recommended before Phase 6.

## Face Recognition (Phase 1, step 3)

**Module:** `backend/app/ai/prototypes/face_recognition.py` — InsightFace
`buffalo_l` (pretrained detection + ArcFace embeddings), cosine similarity
match against a local, gitignored embeddings store
(`app/ai/prototypes/face_db/embeddings.pkl` — biometric data, never
committed), configurable similarity threshold (default 0.45).

**Test 1 — registration + known-face recognition:**
- Registered 1 team member ("Ahmed") by averaging embeddings over 15
  webcam frames.
- Re-ran recognition live on webcam (40 frames, ~1.2 FPS on CPU — face
  detection at 640x640 + embedding is heavier than person detection):
  correctly labeled "Ahmed" every frame a face was visible, similarity
  0.75.

**Test 2 — unknown-face rejection** (2 static images, 4 unregistered
faces total, none in the DB):
- `zidane.jpg`: 2 faces, both correctly labeled "Unknown" (scores 0.10,
  0.06 -- well below the 0.45 threshold).
- `bus.jpg`: 2 of 3 visible faces detected (one obscured by sunglasses/
  angle), both correctly labeled "Unknown" (scores 0.00).
- **4/4 unknown faces correctly rejected.**

**Coverage vs. Section 12's requirement ("3+ registered faces + 2+
unknown"):**
- Unknown-rejection: fully covered (4/4 correct).
- Known-face recognition: only **1 of 3** team members registered so
  far (Khawaja Shees Uddin and Aiman Shahid still need to register) --
  this module is **not fully verified yet**. The checklist item stays
  unchecked until all 3 team members register and a mixed known/unknown
  session is re-run.

**Notes:**
- Registration and the embeddings DB are separate from this test's
  temporary images -- the DB only ever holds explicitly registered team
  members' embeddings, per the proposal's consent-based registration
  requirement.
- Threshold (0.45) is a starting point based on this single test; revisit
  once all 3 team members are registered and a larger true/false match
  rate can be measured.

**Verdict:** PARTIAL PASS -- unknown rejection verified, known-face
recognition verified for 1/3 planned registered faces. Re-test with all
3 team members before marking this module done.

## Restricted-Area (ROI) + Loitering (Phase 1, step 4)

**Module:** `backend/app/ai/prototypes/roi_loitering.py` — YOLOv8n +
ByteTrack (reused from step 2), ROI as a configurable fractional rectangle,
per-track-ID state machine for entry/exit and loiter duration. Alerts fire
once per transition (entry, loiter-threshold-crossed), not every frame.

**Test setup:** 12s webcam clip, 350 frames, one person present throughout.

**Test A — ROI covering the person's position, 3s loiter threshold:**
- `ROI_ENTRY` fired once at frame 0 (person already inside ROI at clip
  start).
- `LOITERING` fired once at frame 20, reported duration 3.1s (correct,
  just past the 3.0s threshold).
- No repeat/duplicate alerts for the remaining 330 frames despite the
  person staying inside the ROI the whole time — confirms the
  single-fire-per-transition logic works.
- Visual check (`frame_0030.png`): ROI rectangle and "restricted area"
  label render correctly; tracked box turns red (inside) vs. green
  (outside); `ID 1` label stable.
- Throughput: 350 frames in 55.1s -> avg 6.3 FPS (YOLO + ByteTrack + ROI
  check, CPU).

**Test B — negative control, ROI in an empty corner (no overlap with the
person), same clip:**
- **0 alerts fired** across all 350 frames — confirms no false triggers
  from a person moving near, but not inside, a restricted zone.

**Verdict:** PASS — entry alert fires once on transition, loitering alert
fires once past threshold, no alert spam, no false positive when the
person never enters the configured zone. Matches Section 12's requirement
("alert fires on entry, not on false triggers from nearby movement";
"loitering alert fires once, not repeatedly spammed").

## Camera Tamper Detection (Phase 1, step 6)

**Module:** `backend/app/ai/prototypes/tamper_detection.py` — rule-based
(brightness, Laplacian-variance sharpness, frame-to-frame diff) against an
EMA-smoothed rolling baseline, state-transition-based alerting (no
trained model).

**Test setup:** 20s/591-frame webcam clip. Manual actions performed partway
through the clip: cover the lens fully with a hand, then move/wave the
hand near the lens, then hold.

**Results (state-change log):**
- Frames 0-465: `normal` throughout (baseline capture window).
- Frame 470: `normal -> moved` — triggered by the frame-diff spike as the
  hand entered frame fast. Correctly fires on the motion-threshold rule,
  but this is motion *near* the camera, not the camera itself being
  physically relocated — see limitation below.
- Frame 475/480: `-> covered` — brightness 44.5 (baseline ~130), sharpness
  8.6 (baseline ~58), frame visually solid dark red (hand fully over
  lens). **Correct, clean match for the "covered" test case.**
- Frame 507 onward: `-> defocused` — brightness back near baseline (~70-80)
  but sharpness collapsed (1-2.3). Visually this is a hand/finger very
  close to (not fully blocking) the lens, not a true optical defocus.
  State stayed `defocused` through the end of the clip (hand not fully
  withdrawn before recording stopped).

**Verdict:** PARTIAL PASS.
- `covered`: confirmed correct, clean signal.
- `moved`: the motion/frame-diff rule fired correctly for fast nearby
  motion, but this isn't the same test as physically relocating the
  camera itself (e.g. knocking it, tilting the mount) — needs a retest
  where the whole camera is moved, not just a hand waved in front of it.
- `defocused`: fired, but the triggering condition (hand very close to,
  not fully covering, the lens) overlaps with "covered" rather than
  testing true lens defocus. The team's webcam has no manual focus
  control, so a true optical-defocus test isn't currently reproducible;
  close-approach blur is being used as a practical proxy in the mock
  environment, consistent with the proposal's "tuned in the mock
  environment" methodology, but this should be called out rather than
  silently treated as equivalent to real defocus.
- **Not checked off in CLAUDE.md Section 14 yet** — retest `moved` with
  an actual camera reposition before marking this module done.

## Camera Health Monitoring (Phase 1, step 7)

**Module:** `backend/app/ai/prototypes/camera_health.py` — read-success
timeout-based online/offline state machine; immediate offline if the
source never opens.

**Test 1 — never opens** (`--source 99`, invalid camera index):
- Status reported `offline` at `t=0.0s`, immediately, no hang. Correct.

**Test 2 — feed loss / disconnect** (video file source, so the stream
ends partway — a practical stand-in for an unplugged/disconnected camera
without needing to physically unplug hardware mid-test; `--timeout 1.0`):
- Status `online` at `t=0.0s` (first frames read successfully).
- Once the file's frames were exhausted, status flipped to `OFFLINE` at
  `t=1.8s` — 0.8s after the 1.0s configured timeout, consistent with the
  ~0.1s poll interval while reads are failing. Correctly detected within
  a reasonable time per Section 12's requirement.

**Verdict:** PASS — both the "never connects" and "feed loss/disconnect"
paths are correctly detected, with offline status reported promptly
(immediately, and ~1.8s after a 1.0s configured timeout respectively).
Timeout is CLI-configurable (`--timeout`), not hardcoded.

## Backend API: Auth / RBAC (Phase 3, step 1)

**Module:** `app/api/auth.py`, `app/api/deps.py`, `app/core/security.py` —
JWT-based auth (PyJWT, HS256, 8h expiry), bcrypt password hashing via
passlib, role-based access control (`admin` / `security_operator`).

**Tests (curl against a local uvicorn instance, port 8010):**
- Login happy path (seeded `admin`/`admin123`): 200, valid JWT returned.
- Login with wrong password: 401.
- Login with nonexistent username: 401.
- `GET /auth/me` with valid token: 200, correct user data returned.
- `GET /auth/me` with no token: 401.
- `GET /auth/me` with a garbage/malformed token: 401.
- `POST /auth/register` as `security_operator` role: **403** — RBAC
  correctly blocks a non-admin from creating accounts.
- `POST /auth/register` as `admin`: **201**, user created.
- `POST /auth/register` with a duplicate username: 400.
- `POST /auth/register` with a password under the 8-char minimum: 422
  (Pydantic validation, rejected before it reaches business logic).

**Verdict:** PASS — happy path and invalid-input cases both return the
correct status codes; RBAC actually restricts the `/auth/register`
endpoint by role, not just by hiding a UI button, per Section 12's
explicit requirement ("Confirm admin vs. security-operator roles
actually restrict access, not just hide UI elements").

## Backend API: CRUD + Alert/Incident Flow (Phase 3, step 2)

**Modules:** `app/api/cameras.py`, `app/api/people.py`, `app/api/alerts.py`,
`app/api/incidents.py`.

**Cameras** (curl, port 8010):
- List (operator token): 200, returns seeded cameras.
- List with no auth token: 401.
- Create as `security_operator`: 403 (admin-only, RBAC enforced).
- Create as `admin`: 201.
- Create with empty `name`: 422 (Pydantic `min_length=1`).
- Get nonexistent camera id: 404.

**People:**
- Create as `security_operator`: 403.
- Create as `admin`: 201.
- List: 200, returns the created record.
- Create with empty `name`: 422.

**Alerts + Incidents (full review flow):**
- Create alert with a nonexistent `camera_id`: 400 (checked against the
  DB before insert, not a raw FK constraint error).
- Create alert with an invalid `priority` ("urgent"): 400.
- Create alert happy path (`loitering`, camera 1): 201.
- List alerts filtered by `camera_id`: 200, returns only that camera's
  alerts.
- Create incident from that alert (`source_alert_id`): 201, alert's
  `incident_id` is set — confirms the human-review-promotes-alert flow
  from Section 11's privacy requirement.
- Create a second incident pointing at the same, already-linked alert:
  400 ("already linked to an incident").
- `PATCH /incidents/{id}/acknowledge`: 200, `status` -> `acknowledged`,
  `acknowledged_by`/`acknowledged_at` set to the current admin user.
- Acknowledge again (already acknowledged): 400.
- `PATCH /incidents/{id}/resolve`: 200, `status` -> `resolved`,
  `resolved_by`/`resolved_at` set.
- Resolve again (already resolved): 400.
- List incidents filtered `status=resolved`: 200, returns the resolved
  incident.

**Verdict:** PASS — all CRUD endpoints enforce RBAC correctly (admin-only
writes on cameras/people), reject invalid input with 400/422 rather than
raw DB errors, and the alert -> incident -> acknowledge -> resolve chain
works end-to-end with correct state transitions and double-action guards.

## WebSocket Real-Time Alerts (Phase 3, step 4)

**Module:** `app/services/ws_manager.py` (in-memory connection registry,
single-process), `app/api/ws.py` (`GET /ws/alerts?token=...`, JWT-gated).
Broadcasts fire on: new alert created, camera status changed, incident
acknowledged/resolved.

**Test 1 — live delivery:** connected a WS client with a valid admin
token, then created an alert via the REST API from a second connection.
The WS client received the new alert's full payload (id, camera_id,
alert_type, priority, message, triggered_at) within the test's 5s
timeout, with no polling/refresh involved.

**Test 2 — auth rejection:** connecting with an invalid/garbage token
was rejected at the handshake (HTTP 403, connection never accepted).

**Verdict:** PASS — dashboard-side clients receive new alerts in real
time without a page refresh, matching Section 12's requirement exactly;
invalid tokens are rejected before the connection is accepted.

## Frontend Dashboard (Phase 4)

**Pages built on TailAdmin, wired to the real backend (not mock data):**
`/signin` (real JWT login), `/cameras`, `/surveillance-alerts`,
`/incidents`, `/people`. Auth state via a React context
(`src/contexts/auth-context.tsx`) backed by `localStorage`; all routes
under `AppLayout` are behind a `ProtectedRoute` that redirects to
`/signin` when logged out. API calls isolated in `src/services/`
(never inline `fetch` in components), live updates via
`src/hooks/use-alerts-socket.ts`.

**Test method:** headless Chrome driven directly over the Chrome
DevTools Protocol (no browser-automation tool was available in this
environment, so a raw CDP WebSocket client was scripted) against the
real Vite dev server and FastAPI backend together.

**Results:**
- Sign-in form renders, accepts `admin`/`admin123`, redirects to `/`
  on success. `ProtectedRoute` confirmed working (unauthenticated
  requests for any dashboard route redirect to `/signin`).
- `/cameras`: renders the real seeded cameras (`Test Camera 1`,
  `Test Camera 2`) from the database, with status badges and an
  admin-only "Add Camera" dialog.
- `/surveillance-alerts`: renders real alerts created earlier via the
  API (including one already linked to an incident, correctly shown as
  "incident created" instead of the promote button).
- `/incidents`: renders the real incident from earlier testing,
  correctly showing status `resolved` and "Done" (no stray
  acknowledge/resolve buttons on a closed incident).
- `/people`: renders the real registered person ("Ahmed") with an
  admin-only "Register Person" dialog.
- Zero console errors or uncaught exceptions captured via CDP
  (`Runtime.exceptionThrown` / `Runtime.consoleAPICalled`) during the
  full login -> cameras -> alerts -> incidents -> people walkthrough.
- `npm run build` (`tsc -b && vite build`) passes with zero type
  errors across all new/modified files.

**Known gaps (not yet done, explicitly deferred):**
- Settings page (ROI/loitering threshold/tamper sensitivity configurable
  from the UI) — not built yet; these are still argparse CLI flags on
  the Phase 1 AI scripts, not persisted backend settings, so there is
  nothing real yet for a settings UI to control.
- Live WebSocket update *inside the browser* (new alert appearing
  without a refresh while a human is looking at the page) was verified
  at the backend level (see the WebSocket section above) but not
  re-verified end-to-end through the actual rendered dashboard in this
  pass -- the frontend hook (`use-alerts-socket.ts`) prepends/patches
  state on `alert`/`camera_status`/`incident_update` messages the same
  way the backend test proved those messages arrive, but a dedicated
  two-browser-tab test is still worth doing before Phase 6.

**Verdict:** PASS for what was built and tested -- a real, backend-wired
dashboard a supervisor can click through (not a mockup), covering
sections 1-5 of Phase 4's plan.

## Settings Page + Dashboard Cleanup (Phase 4, step 6 + polish)

**Backend:** new `camera_settings` table (one row per camera, migration
`a7a79d74c895`) holding ROI rectangle (x1/y1/x2/y2 fractions),
loitering threshold, and the 3 tamper-sensitivity ratios used by
`roi_loitering.py` and `tamper_detection.py`'s CLI flags.
`GET /cameras/{id}/settings` creates a default row on first read;
`PUT` is admin-only and validates `roi_x1 < roi_x2` / `roi_y1 < roi_y2`
(422 on violation), consistent with the "configurable rules, not
hardcoded" standard in Section 11.

**Tests (curl):**
- `GET` on a camera with no settings yet: 200, returns defaults and
  persists them.
- `PUT` as `security_operator`: 403.
- `PUT` as `admin` with valid values: 200, values persisted (re-`GET`
  confirms).
- `PUT` with `roi_x1 > roi_x2`: 422 (model validator catches inverted
  ROI before it's saved).
- `GET`/`PUT` on a nonexistent camera id: 404.

**Frontend:** new `/settings` page -- camera picker + a form for all 9
thresholds, admin-only edit (operators see the form read-only via a
disabled `<fieldset>`, not just a hidden button). Verified via the same
headless-Chrome/CDP method as the rest of Phase 4: loads real saved
values, camera picker shows the camera's name (fixed a first pass where
it rendered the raw id instead, via `SelectValue`'s render-prop
pattern), zero console errors.

**Dashboard cleanup** (explicit request: keep what the project needs
now or later, remove everything else so the dashboard reads clean for
a supervisor demo):
- Removed from nav + routes: Calendar, Profile, Forms, Tables, Charts
  (bar/line demo), UI Elements showcase (alerts/avatars/badges/
  buttons/images/videos), Blank page, Sign Up (registration is
  admin-only via the API, there's no self-service signup flow to link
  to), and the sidebar's "Purchase Plan" TailAdmin upsell widget.
- Replaced the Ecommerce demo homepage with a real Overview page
  (stat cards + recent alerts, wired to the actual API).
- Replaced the notification bell's hardcoded fake "team activity" data
  (people commenting on fake projects) with real recent alerts, since
  showing fabricated activity data in a security-system demo would be
  actively misleading.
- Bundle size dropped from ~2.73 MB to ~810 KB (gzip ~799 KB -> ~249 KB)
  as a side effect of removing ~400 unused modules -- a signal the
  cleanup actually removed dead code, not just hid it.

**Verdict:** PASS. Phase 4 is now fully done (all 6 steps), and the
dashboard only contains pages that map to an actual project requirement
or a already-built feature.

## Phase 3 step 3 — Wire Phase 1 AI scripts into backend (2026-11-17)

**What changed:** `roi_loitering.py` and `tamper_detection.py` previously
only read thresholds from CLI flags and printed alerts to console. Added
`backend/app/ai/prototypes/backend_client.py` (a thin `requests`-based
client: login once, `GET /cameras/{id}/settings`, `POST /alerts`) and an
optional `--camera-id` flag on both scripts. When `--camera-id` is given
(plus `--api-username`/`--api-password` or the `UNIVERSE_API_USERNAME`/
`UNIVERSE_API_PASSWORD` env vars), each script fetches its ROI/loiter/
tamper thresholds from the real `camera_settings` table at startup
instead of CLI defaults, and POSTs a real alert to `/alerts` (through the
same validated endpoint the dashboard uses, so the existing camera_id/
priority checks and the WebSocket broadcast all fire normally) in
addition to the existing console print. Without `--camera-id`, both
scripts behave exactly as before (CLI-only, console-only) -- this was
checked explicitly so the existing Phase 1 standalone test results above
stay valid.

**How tested:**
1. Direct `backend_client.py` test: logged in as `operator`, fetched
   camera 1's settings (returned the real saved values from the Settings
   page test: `roi=0.2,0.1,0.9,0.9`, `loiter_seconds=8.0`, `tamper_motion_
   threshold=30.0`, etc. -- confirming it reads live DB state, not
   defaults), then POSTed a test alert (`TEST_INTEGRATION`, id 3) and
   confirmed it via a separate `GET /alerts?camera_id=1` call (persisted,
   not just an echoed response).
2. `roi_loitering.py --source 0 --camera-id 1 --headless --max-frames 20`:
   printed `Loaded settings from backend for camera 1: roi=0.2,0.1,0.9,0.9
   loiter_seconds=8.0` (matches step 1's values), fired a real `ROI_ENTRY`
   alert on frame 0, confirmed as alert id 4 in the DB afterward with the
   correct `camera_id`, `alert_type`, `priority`, and `message`.
3. `tamper_detection.py --source 0 --camera-id 1 --headless --max-frames
   15`: printed `Loaded tamper thresholds from backend for camera 1:
   motion=30.0 covered_brightness=0.4 covered_sharpness=0.3 defocus_
   sharpness=0.35` (matches saved settings), ran cleanly with 0 state
   changes (camera was in its normal resting state, as expected --
   confirms the settings-load and run path don't crash, but did not
   itself re-exercise a tamper state transition through this new code
   path; the POST-alert mechanism itself is already proven generically by
   steps 1-2 since both scripts call the identical `client.post_alert`
   method).
4. Backward-compat check: `roi_loitering.py --source 0 --headless
   --max-frames 10` (no `--camera-id`) printed no "Loaded settings" line
   and made no backend calls -- confirms standalone CLI-only mode, used
   for all of Phase 1's original evaluation above, is unchanged.

**Verdict:** PASS for the wiring itself (settings read from DB, alerts
written to DB via the real API, backward compatibility preserved).
**Not yet exercised:** a live tamper state transition (cover/move/
defocus) through the new `--camera-id` path specifically -- only the
settings-load and no-crash path was confirmed for `tamper_detection.py`
in this session. Should be re-confirmed the next time the team does a
physical tamper retest (see the still-open Phase 1 step 6 item below).

## Phase 5 — Full-pipeline integration (2026-11-17)

**What was tested:** the complete chain from CLAUDE.md Phase 5 step 1 --
camera -> AI detection -> alert -> DB -> WebSocket -> dashboard ->
operator acknowledges/resolves -- with no manual DB edits anywhere, and
every step going through real code (not mocked or faked).

**Method:** a headless Chrome tab (driven over the raw Chrome DevTools
Protocol -- no browser-automation MCP tool is available in this
environment, see the note under "Phase 4 step 6" above) logged in as
`operator` and opened the real `/surveillance-alerts` page, left running.
While that tab stayed open (no reload), `roi_loitering.py --source 0
--camera-id 1 --headless --max-frames 15 --api-username operator
--api-password operator123` was run against the real webcam in a
separate process.

**Result, step by step:**
1. Baseline: 4 alert rows on the page before the script ran.
2. Script fired a real `ROI_ENTRY` alert (person detected in the
   configured ROI, frame 0) and POSTed it to the backend via
   `backend_client.py` (Phase 3 step 3's wiring).
3. Without any page refresh, the open browser tab's row count went to
   5 and the new row's text matched the just-fired alert exactly
   (`ROI_ENTRY`, camera #1, "Person (track 1) entered restricted area")
   -- confirms the WebSocket push reached the live rendered dashboard,
   not just the backend-level WS test done earlier.
4. Clicked that row's "Create Incident" button (real UI click, not an
   API call from the test script) -> incident created.
5. Navigated to `/incidents`: the new incident showed `status: open`.
6. Clicked "Acknowledge" -> row updated to `status: acknowledged`
   (UI-driven, via `PATCH /incidents/{id}/acknowledge`).
7. Clicked "Resolve" -> row updated to `status: resolved`, action
   column showed "Done".
8. Verified independently via a plain `GET /incidents` API call
   afterward (not through the test UI): incident id 3 --
   `status: "resolved"`, `acknowledged_by: 2`, `resolved_by: 2` (the
   operator's user id), `acknowledged_at` before `resolved_at`,
   `updated_at` matching the resolve timestamp. No row was ever touched
   directly in the database.
9. Zero `Runtime.exceptionThrown` or console error/warning events
   captured across the whole flow.

**Verdict:** PASS. The full Phase 5 step 1 pipeline runs end-to-end
through real code with no manual DB edits. This also closes the
previously-open "dedicated live-WebSocket-in-browser test" item from the
Phase 4 section above -- the alert delivery was observed live in an
actual rendered dashboard tab, not just at the backend level.

**Not yet done (Phase 5 step 2 / Phase 6):** this was a single clean
run with one person/track in frame. No FPS/accuracy numbers were
collected here -- that is Phase 6's job and still needs the team's
physical mock-camera setup.

## Phase 5 step 2 — Concurrency + a real timing bug found and fixed (2026-11-17)

**Concurrency test:** 20 concurrent `POST /alerts` requests fired from
20 threads (alternating `camera_id` 1/2) against the running backend.
Result: 20/20 succeeded, 20 unique alert ids (no collisions), zero
errors -- the alert-creation path is safe under concurrent load, no
race condition or lost-write found.

**Timing bug found:** every single HTTP call to the backend (GET or
POST, concurrent or not) was taking a flat ~2.0s, regardless of what
the endpoint did -- including `GET /cameras`, which does nothing slow.
Root cause: `backend_client.py` (and the frontend's `.env`) pointed at
`http://localhost:8000`; on this Windows machine, resolving `localhost`
tries the IPv6 address (`::1`) first, which the backend isn't listening
on (confirmed via `netstat`: only `127.0.0.1:8000`, no `::1:8000`), so
every connection attempt waits out an IPv6 connect timeout (~2s) before
falling back to IPv4. This is exactly the kind of cross-module timing
bug Phase 5 step 2 exists to catch -- it only shows up once something
is actually calling the running backend over the network, not in any
single-module test.

**Fix:** changed the default `--api-base` in `backend_client.py`, and
`VITE_API_BASE_URL`/`VITE_WS_BASE_URL` in `frontend/.env` +
`.env.example`, from `localhost` to `127.0.0.1`. Re-measured: 3
sequential `POST /alerts` calls dropped from ~2.03-2.05s each to
0.004-0.011s each (roughly 200-400x faster). This directly matters for
the "processing latency" metric Phase 6 needs to measure -- without
this fix, every AI-script-generated alert would have carried a ~2s
artificial delay that has nothing to do with detection, tracking, or
the database.

**Note:** `frontend/.env` is gitignored (not committed); the running
frontend dev server needs a restart to pick up the new value, which was
left for the user to do since they have it open and were actively
testing it themselves this session.

**Verdict:** PASS for concurrency safety. Real bug found and fixed for
latency.

## Phase 6 — Testing & Evaluation: Section 12 table consolidated (2026-11-17)

CLAUDE.md Section 12's testing table requires every module to be
verified a specific way before it's "done." Most rows were already
tested individually in the sections above; this pulls them into one
place, exactly as Phase 6 step 1 asks for, and is honest about which
rows are not actually closed yet.

| Module | Required check | Status |
|---|---|---|
| Person detection | Recorded clip + live webcam, stable boxes, FPS | **PASS** -- see "Person Detection" above: ~6 FPS (clip), ~4.3 FPS (live webcam), CPU, YOLOv8n |
| Tracking | IDs stay consistent across frames, count ID switches | **PASS** for single continuously-visible person (0 ID switches). **Not done:** multi-person/occlusion re-acquisition case -- needs the team physically present |
| Face recognition | 3+ registered + 2+ unknown faces, true/false match rate | **BLOCKED** -- only 1/3 team members registered (Ahmed). Unknown-rejection alone is PASS (4/4). Needs Khawaja + Aiman to register their faces |
| Loitering detection | Alert fires once past threshold, not spammed | **PASS** -- see "ROI + Loitering" above: fired once at 3.1s on a 3s threshold |
| Restricted-area (ROI) | Alert fires on entry, no false triggers from nearby movement | **PASS** -- 0 false triggers in the negative-control test |
| Camera tamper detection | Cover/move/defocus each trigger the right alert type | **PARTIAL** -- `covered` is clean. `moved`/`defocused` were triggered by hand motion near the lens, not a true reposition/optical defocus. **BLOCKED** on a physical camera-reposition retest |
| Camera health monitoring | Offline detected within a reasonable time after disconnect | **PASS** -- never-opens at t=0.0s, feed-loss ~1.8s after a 1.0s timeout |
| Backend API endpoints | Postman-style happy path + invalid input, before frontend | **PASS** -- see "Backend API" sections: auth, CRUD, alert/incident flow all tested via curl (200/400/401/403/404 as expected) |
| WebSocket alerts | Dashboard receives a new alert live, no refresh | **PASS** -- confirmed twice: backend-level WS test, and the real rendered-dashboard case in the Phase 5 full-pipeline test above |
| Auth / RBAC | Admin vs. operator roles actually restrict access, not just hide UI | **PASS** -- admin-only writes return 403 for operator at the API layer (see "Backend API: Auth / RBAC" above), not just a hidden button |
| Full integration | camera -> detection -> alert -> dashboard -> acknowledge/resolve, no manual DB edits | **PASS** -- see "Phase 5 -- Full-pipeline integration" above |

**9 of 11 rows: PASS.** 1 row PARTIAL (tamper). 1 row BLOCKED (face
recognition, only 1/3 registered). Both remaining gaps need physical
team presence (Khawaja/Aiman registering their faces; the camera itself
being physically moved for a clean tamper retest) and cannot be closed
solo.

**Still entirely outstanding for Phase 6** (needs the team's physical
mock-environment, not just the above table): a controlled multi-scenario
accuracy pass (varying lighting, distance, occlusion) with
precision/recall/F1 numbers written up, rather than the single-run
pass/fail checks above.
