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
