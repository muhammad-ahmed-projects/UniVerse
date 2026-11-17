"""Phase 1 prototype: camera tamper detection (covered / moved / defocused).

Rule-based, no trained model: tracks brightness, sharpness (Laplacian
variance), and frame-to-frame difference against a rolling baseline
captured while the camera is in its normal state. An alert fires once
per state transition, not every frame.

Standalone script, not yet wired into the FastAPI backend. Run directly:
    python -m app.ai.prototypes.tamper_detection --source 0
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np


def compute_metrics(gray: np.ndarray) -> tuple[float, float]:
    brightness = float(np.mean(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return brightness, sharpness


def classify_state(
    brightness: float, sharpness: float, frame_diff: float,
    baseline_brightness: float, baseline_sharpness: float, args: argparse.Namespace,
) -> str:
    if frame_diff > args.motion_threshold:
        return "moved"
    if (
        brightness < baseline_brightness * args.covered_brightness_ratio
        and sharpness < baseline_sharpness * args.covered_sharpness_ratio
    ):
        return "covered"
    if (
        sharpness < baseline_sharpness * args.defocus_sharpness_ratio
        and abs(brightness - baseline_brightness) < args.brightness_tolerance
    ):
        return "defocused"
    return "normal"


def run(args: argparse.Namespace) -> None:
    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {args.source}")

    out_dir = Path(args.save_frames) if args.save_frames else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    baseline_brightness: float | None = None
    baseline_sharpness: float | None = None
    prev_gray = None
    current_state = "normal"
    events: list[tuple[int, str, str]] = []

    frame_idx = 0
    t_start = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness, sharpness = compute_metrics(gray)
        frame_diff = float(np.mean(cv2.absdiff(gray, prev_gray))) if prev_gray is not None else 0.0

        if baseline_brightness is None:
            baseline_brightness, baseline_sharpness = brightness, sharpness

        new_state = classify_state(brightness, sharpness, frame_diff, baseline_brightness, baseline_sharpness, args)

        if new_state != current_state:
            events.append((frame_idx, current_state, new_state))
            print(f"[frame {frame_idx}] TAMPER STATE CHANGE: {current_state} -> {new_state}")
            current_state = new_state

        if current_state == "normal":
            baseline_brightness = 0.95 * baseline_brightness + 0.05 * brightness
            baseline_sharpness = 0.95 * baseline_sharpness + 0.05 * sharpness

        cv2.putText(frame, f"state: {current_state}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, f"brightness: {brightness:.1f}  sharpness: {sharpness:.1f}  diff: {frame_diff:.1f}",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        if out_dir and frame_idx % args.frame_sample_every == 0:
            cv2.imwrite(str(out_dir / f"frame_{frame_idx:04d}.png"), frame)

        if not args.headless:
            cv2.imshow("UniVerse - Tamper Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        prev_gray = gray
        frame_idx += 1
        if args.max_frames and frame_idx >= args.max_frames:
            break

    elapsed = max(time.time() - t_start, 1e-6)
    print(f"Processed {frame_idx} frames in {elapsed:.1f}s (avg FPS: {frame_idx / elapsed:.1f})")
    print("State change events:")
    for e in events:
        print(" -", e)

    cap.release()
    if not args.headless:
        cv2.destroyAllWindows()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UniVerse Phase 1: camera tamper detection prototype")
    parser.add_argument("--source", default="0", help="Webcam index or video file path")
    parser.add_argument("--motion-threshold", type=float, default=25.0, help="Mean abs frame-diff above this = camera moved")
    parser.add_argument("--covered-brightness-ratio", type=float, default=0.4, help="Brightness below baseline*ratio counts toward 'covered'")
    parser.add_argument("--covered-sharpness-ratio", type=float, default=0.3, help="Sharpness below baseline*ratio counts toward 'covered'")
    parser.add_argument("--defocus-sharpness-ratio", type=float, default=0.35, help="Sharpness below baseline*ratio (brightness unchanged) counts as 'defocused'")
    parser.add_argument("--brightness-tolerance", type=float, default=15.0, help="Max brightness delta from baseline still considered 'defocused' rather than 'covered'")
    parser.add_argument("--headless", action="store_true", help="Run without a display window (for automated testing)")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 = unlimited)")
    parser.add_argument("--save-frames", default="", help="Directory to save sample annotated frames")
    parser.add_argument("--frame-sample-every", type=int, default=10, help="Save every Nth frame when --save-frames is set")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
