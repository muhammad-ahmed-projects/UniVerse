"""Phase 1 prototype: person detection + ByteTrack -> stable IDs per person.

Standalone script, not yet wired into the FastAPI backend. Run directly:
    python -m app.ai.prototypes.tracking --source 0
"""
import argparse
import time
from pathlib import Path

import cv2

from app.ai.prototypes.person_detection import PERSON_CLASS_ID, load_model, open_source

ID_COLOR_PALETTE = [
    (0, 255, 0), (255, 128, 0), (0, 128, 255), (255, 0, 255),
    (0, 255, 255), (128, 0, 255), (255, 255, 0), (0, 128, 0),
]


def color_for_id(track_id: int) -> tuple[int, int, int]:
    return ID_COLOR_PALETTE[track_id % len(ID_COLOR_PALETTE)]


def draw_tracks(frame, result, conf_threshold: float, seen_ids: set[int]) -> int:
    count = 0
    boxes = result.boxes
    if boxes is None or boxes.id is None:
        return 0
    for box, track_id in zip(boxes, boxes.id):
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        if cls_id != PERSON_CLASS_ID or conf < conf_threshold:
            continue
        tid = int(track_id)
        seen_ids.add(tid)
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        color = color_for_id(tid)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame, f"ID {tid} ({conf:.2f})", (x1, max(y1 - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
        )
        count += 1
    return count


def run(args: argparse.Namespace) -> None:
    model = load_model(args.model)
    cap = open_source(args.source)

    writer = None
    if args.save_video:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps_out = cap.get(cv2.CAP_PROP_FPS) or 20.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(args.save_video, fourcc, fps_out, (width, height))

    out_dir = Path(args.save_frames) if args.save_frames else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    seen_ids: set[int] = set()
    frame_idx = 0
    fps_smoothed = 0.0
    t_start = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        t0 = time.time()
        result = model.track(
            frame, persist=True, tracker=args.tracker, classes=[PERSON_CLASS_ID],
            conf=args.conf, verbose=False,
        )[0]
        person_count = draw_tracks(frame, result, args.conf, seen_ids)
        dt = max(time.time() - t0, 1e-6)
        instant_fps = 1.0 / dt
        fps_smoothed = instant_fps if fps_smoothed == 0 else 0.9 * fps_smoothed + 0.1 * instant_fps

        cv2.putText(
            frame, f"FPS: {fps_smoothed:.1f}  people: {person_count}  total IDs: {len(seen_ids)}",
            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2,
        )

        if writer:
            writer.write(frame)
        if out_dir and frame_idx % args.frame_sample_every == 0:
            cv2.imwrite(str(out_dir / f"frame_{frame_idx:04d}.png"), frame)

        if not args.headless:
            cv2.imshow("UniVerse - Tracking", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        frame_idx += 1
        if args.max_frames and frame_idx >= args.max_frames:
            break

    elapsed = max(time.time() - t_start, 1e-6)
    print(f"Processed {frame_idx} frames in {elapsed:.1f}s (avg FPS: {frame_idx / elapsed:.1f})")
    print(f"Unique track IDs assigned: {len(seen_ids)} -> {sorted(seen_ids)}")

    cap.release()
    if writer:
        writer.release()
    if not args.headless:
        cv2.destroyAllWindows()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UniVerse Phase 1: person tracking prototype (ByteTrack)")
    parser.add_argument("--source", default="0", help="Webcam index or video file path")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLO weights file")
    parser.add_argument("--tracker", default="bytetrack.yaml", help="Ultralytics tracker config (bytetrack.yaml or botsort.yaml)")
    parser.add_argument("--conf", type=float, default=0.5, help="Confidence threshold for person detections")
    parser.add_argument("--headless", action="store_true", help="Run without a display window (for automated testing)")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 = unlimited)")
    parser.add_argument("--save-video", default="", help="Path to save the annotated output video")
    parser.add_argument("--save-frames", default="", help="Directory to save sample annotated frames")
    parser.add_argument("--frame-sample-every", type=int, default=15, help="Save every Nth frame when --save-frames is set")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
