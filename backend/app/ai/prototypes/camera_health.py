"""Phase 1 prototype: camera health monitoring (offline / feed loss).

Flags a camera as offline immediately if it never opens, or after a
configurable timeout with no successful frame read (covers disconnect,
feed loss, and a stream that simply ends). Status changes are logged
once per transition, not every frame.

Standalone script, not yet wired into the FastAPI backend. Run directly:
    python -m app.ai.prototypes.camera_health --source 0
"""
import argparse
import time

import cv2


def run(args: argparse.Namespace) -> None:
    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    t_start = time.time()
    status = "online" if cap.isOpened() else "offline"
    print(f"[t=0.0s] camera status: {status}")
    if status == "offline":
        return

    last_ok_time = t_start
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        now = time.time()

        if ok:
            last_ok_time = now
            if status != "online":
                print(f"[t={now - t_start:.1f}s] camera status: online (feed restored)")
                status = "online"
        elif now - last_ok_time > args.timeout and status != "offline":
            print(f"[t={now - t_start:.1f}s] camera status: OFFLINE (no frame for over {args.timeout}s)")
            status = "offline"

        if not args.headless and ok:
            cv2.imshow("UniVerse - Camera Health", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        if not ok:
            time.sleep(0.1)  # avoid a tight busy-loop while reads keep failing

        frame_idx += 1
        if args.max_frames and frame_idx >= args.max_frames:
            break
        if args.max_seconds and now - t_start >= args.max_seconds:
            break

    cap.release()
    if not args.headless:
        cv2.destroyAllWindows()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UniVerse Phase 1: camera health monitoring prototype")
    parser.add_argument("--source", default="0", help="Webcam index or video file path")
    parser.add_argument("--timeout", type=float, default=2.0, help="Seconds without a successful frame before flagging offline")
    parser.add_argument("--headless", action="store_true", help="Run without a display window (for automated testing)")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frame-read attempts (0 = unlimited)")
    parser.add_argument("--max-seconds", type=float, default=0, help="Stop after N seconds (0 = unlimited)")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
