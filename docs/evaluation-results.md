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
