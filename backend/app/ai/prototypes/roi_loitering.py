"""Phase 1 prototype: restricted-area (ROI) entry + loitering alerts.

Builds on the tracking prototype -- each tracked person's box center is
checked against a configured zone. Alerts fire once per transition
(entry / loitering-threshold-crossed), not every frame.

Runs standalone with CLI flags by default:
    python -m app.ai.prototypes.roi_loitering --source 0 --roi 0.3,0.2,0.9,1.0

Or wired to the backend (reads roi/loiter_seconds from camera_settings,
writes real alerts via POST /alerts instead of only printing):
    python -m app.ai.prototypes.roi_loitering --source 0 --camera-id 1 \
        --api-username operator --api-password operator123
"""

import argparse
import time
from pathlib import Path

import cv2

from app.ai.prototypes.backend_client import add_backend_args, build_client
from app.ai.prototypes.person_detection import PERSON_CLASS_ID, load_model, open_source

Roi = tuple[int, int, int, int]


def parse_roi(roi_str: str, width: int, height: int) -> Roi:
    x1f, y1f, x2f, y2f = map(float, roi_str.split(","))
    return int(x1f * width), int(y1f * height), int(x2f * width), int(y2f * height)


def box_center(box) -> tuple[int, int]:
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    return (x1 + x2) // 2, (y1 + y2) // 2


def point_in_roi(point: tuple[int, int], roi: Roi) -> bool:
    x, y = point
    rx1, ry1, rx2, ry2 = roi
    return rx1 <= x <= rx2 and ry1 <= y <= ry2


def run(args: argparse.Namespace) -> None:
    client = build_client(args)
    loiter_seconds = args.loiter_seconds
    roi_str = args.roi
    if client is not None:
        settings = client.get_camera_settings(args.camera_id)
        roi_str = f"{settings['roi_x1']},{settings['roi_y1']},{settings['roi_x2']},{settings['roi_y2']}"
        loiter_seconds = settings["loiter_seconds"]
        print(
            f"Loaded settings from backend for camera {args.camera_id}: roi={roi_str} loiter_seconds={loiter_seconds}"
        )

    model = load_model(args.model)
    cap = open_source(args.source)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    roi = parse_roi(roi_str, width, height)

    track_state: dict[int, dict] = {}
    alerts: list[tuple[int, str, int]] = []

    out_dir = Path(args.save_frames) if args.save_frames else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    frame_idx = 0
    t_start = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        result = model.track(
            frame,
            persist=True,
            tracker=args.tracker,
            classes=[PERSON_CLASS_ID],
            conf=args.conf,
            verbose=False,
        )[0]
        now = time.time()

        cv2.rectangle(frame, (roi[0], roi[1]), (roi[2], roi[3]), (255, 255, 0), 2)
        cv2.putText(
            frame, "restricted area", (roi[0], max(roi[1] - 8, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1
        )

        boxes = result.boxes
        if boxes is not None and boxes.id is not None:
            for box, track_id in zip(boxes, boxes.id, strict=True):
                tid = int(track_id)
                inside = point_in_roi(box_center(box), roi)
                state = track_state.setdefault(tid, {"inside": False, "entered_at": None, "loiter_alerted": False})

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                color = (0, 0, 255) if inside else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"ID {tid}", (x1, max(y1 - 8, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                if inside and not state["inside"]:
                    alerts.append((frame_idx, "ROI_ENTRY", tid))
                    print(f"[frame {frame_idx}] ALERT: ID {tid} entered restricted area")
                    if client is not None:
                        client.post_alert(
                            args.camera_id,
                            "ROI_ENTRY",
                            "medium",
                            f"Person (track {tid}) entered restricted area",
                            extra_data={"track_id": tid, "frame": frame_idx},
                        )
                    state["entered_at"] = now
                    state["loiter_alerted"] = False
                elif not inside and state["inside"]:
                    state["entered_at"] = None
                    state["loiter_alerted"] = False

                if inside and state["entered_at"] is not None:
                    duration = now - state["entered_at"]
                    if duration >= loiter_seconds and not state["loiter_alerted"]:
                        alerts.append((frame_idx, "LOITERING", tid))
                        print(f"[frame {frame_idx}] ALERT: ID {tid} loitering for {duration:.1f}s")
                        if client is not None:
                            client.post_alert(
                                args.camera_id,
                                "LOITERING",
                                "high",
                                f"Person (track {tid}) loitering for {duration:.1f}s",
                                extra_data={"track_id": tid, "frame": frame_idx, "duration_seconds": duration},
                            )
                        state["loiter_alerted"] = True

                state["inside"] = inside

        if out_dir and frame_idx % args.frame_sample_every == 0:
            cv2.imwrite(str(out_dir / f"frame_{frame_idx:04d}.png"), frame)

        if not args.headless:
            cv2.imshow("UniVerse - ROI / Loitering", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        frame_idx += 1
        if args.max_frames and frame_idx >= args.max_frames:
            break

    elapsed = max(time.time() - t_start, 1e-6)
    print(f"Processed {frame_idx} frames in {elapsed:.1f}s (avg FPS: {frame_idx / elapsed:.1f})")
    print(f"Total alerts fired: {len(alerts)}")
    for a in alerts:
        print(" -", a)

    cap.release()
    if not args.headless:
        cv2.destroyAllWindows()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UniVerse Phase 1: ROI + loitering prototype")
    parser.add_argument("--source", default="0", help="Webcam index or video file path")
    parser.add_argument("--model", default="yolov8n.pt", help="YOLO weights file")
    parser.add_argument("--tracker", default="bytetrack.yaml", help="Ultralytics tracker config")
    parser.add_argument("--conf", type=float, default=0.5, help="Confidence threshold for person detections")
    parser.add_argument("--roi", default="0.5,0.0,1.0,1.0", help="x1,y1,x2,y2 as fractions of frame size")
    parser.add_argument(
        "--loiter-seconds", type=float, default=5.0, help="Seconds inside the ROI before a loitering alert fires"
    )
    parser.add_argument("--headless", action="store_true", help="Run without a display window (for automated testing)")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frames (0 = unlimited)")
    parser.add_argument("--save-frames", default="", help="Directory to save sample annotated frames")
    parser.add_argument(
        "--frame-sample-every", type=int, default=15, help="Save every Nth frame when --save-frames is set"
    )
    add_backend_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
