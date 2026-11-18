"""Camera health monitoring (offline / feed loss / restore).

Flags a camera offline immediately if it can't be opened, or after a
configurable timeout with no successful frame read (covers disconnect,
feed loss, and a stream that simply ends). While offline it retries
opening the source every --retry-seconds, so a camera that reboots or is
plugged back in is detected as online again. Status changes are logged
once per transition, not every frame.

Standalone (console only):
    python -m app.ai.prototypes.camera_health --source 0

Wired to the backend (reports status via POST /cameras/{id}/heartbeat,
which updates the dashboard live, and raises CAMERA_OFFLINE /
CAMERA_ONLINE alerts on transitions). It also streams the raw feed to the
dashboard's Live View at low priority, so a detection script running on
the same camera (whose frames carry boxes and names) takes the view over:
    python -m app.ai.prototypes.camera_health --source 0 --camera-id 1

Note: a USB webcam can only be opened by one process at a time on
Windows, so run this OR a detection script against the same webcam. IP
cameras (RTSP) accept multiple connections.
"""

import argparse
import time

import cv2

from app.ai.prototypes.backend_client import BackendClient, add_backend_args, build_client


def open_capture(source: str) -> cv2.VideoCapture:
    return cv2.VideoCapture(int(source) if source.isdigit() else source)


def report(
    client: BackendClient | None,
    old: str | None,
    new: str,
    elapsed: float,
    timeout: float,
) -> None:
    reason = (
        "" if new == "online" else f" (no frame for over {timeout}s)" if old == "online" else " (could not open source)"
    )
    print(f"[t={elapsed:.1f}s] camera status: {new.upper() if new == 'offline' else new}{reason}")
    if client is None:
        return
    client.heartbeat(new)
    # No evidence images: there's no frame while offline, and "restored" needs none.
    if new == "offline":
        client.post_alert(
            "CAMERA_OFFLINE",
            "high",
            f"Camera went offline{reason}",
            extra_data={"previous_status": old},
            evidence=False,
        )
    elif old == "offline":
        client.post_alert(
            "CAMERA_ONLINE", "low", "Camera feed restored", extra_data={"previous_status": old}, evidence=False
        )


def run(args: argparse.Namespace) -> None:
    client = build_client(args, "camera_health", stream_priority=0)
    t_start = time.time()
    cap = open_capture(args.source)
    status = "online" if cap.isOpened() else "offline"
    report(client, None, status, 0.0, args.timeout)

    last_ok_time = t_start
    last_retry_time = t_start
    last_heartbeat_time = t_start
    frame_idx = 0

    while True:
        now = time.time()
        ok, frame = cap.read() if cap.isOpened() else (False, None)

        if ok:
            last_ok_time = now
            if client is not None:
                client.publish_frame(frame)
            if status != "online":
                report(client, status, "online", now - t_start, args.timeout)
                status = "online"
            elif client is not None and now - last_heartbeat_time >= args.heartbeat_seconds:
                # Periodic heartbeat keeps cameras.last_seen_at fresh while online.
                client.heartbeat("online")
                last_heartbeat_time = now
        else:
            if status != "offline" and now - last_ok_time > args.timeout:
                report(client, status, "offline", now - t_start, args.timeout)
                status = "offline"
            if status == "offline" and args.retry_seconds > 0 and now - last_retry_time >= args.retry_seconds:
                cap.release()
                cap = open_capture(args.source)
                last_retry_time = now
                last_ok_time = now  # give the reopened source a full timeout window
            time.sleep(0.1)  # avoid a tight busy-loop while reads keep failing

        if not args.headless and ok:
            cv2.imshow("UniVerse - Camera Health", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        frame_idx += 1
        if args.max_frames and frame_idx >= args.max_frames:
            break
        if args.max_seconds and now - t_start >= args.max_seconds:
            break

    cap.release()
    if client is not None:
        client.close()
    if not args.headless:
        cv2.destroyAllWindows()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UniVerse: camera health monitoring")
    parser.add_argument("--source", default="0", help="Webcam index, video file path, or RTSP URL")
    parser.add_argument(
        "--timeout", type=float, default=2.0, help="Seconds without a successful frame before flagging offline"
    )
    parser.add_argument(
        "--retry-seconds",
        type=float,
        default=5.0,
        help="While offline, try reopening the source this often (0 = never)",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=10.0,
        help="While online, refresh last_seen_at on the backend this often",
    )
    parser.add_argument("--headless", action="store_true", help="Run without a display window (for automated testing)")
    parser.add_argument("--max-frames", type=int, default=0, help="Stop after N frame-read attempts (0 = unlimited)")
    parser.add_argument("--max-seconds", type=float, default=0, help="Stop after N seconds (0 = unlimited)")
    add_backend_args(parser)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
